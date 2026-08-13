import json
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional
from sklearn.metrics import precision_score, recall_score, f1_score

from classifier_utils import load_image_paths, STATS_PATH, HEATMAPS_DIR
from classifier_svm import train_svm, load_svm, predict_svm
from classifier_cnn import train_cnn, load_cnn, predict_cnn
from classifier_vit import train_vit, load_vit, predict_vit
from augmentation import get_augmentations, parse_group_id

# ── Training & Evaluation ────────────────────────────────────────────────────
def train_and_evaluate():
    paths, labels = load_image_paths()
    if not paths:
        raise ValueError("No images found in the DB folder. Please upload images first.")
    
    import numpy as np
    
    n_good = labels.count(0)
    n_damaged = labels.count(1)
    unique_labels = len(np.unique(labels))
    
    # Log warning if only one class available (training will still work but results may be limited)
    if unique_labels < 2:
        print(f"[WARN] Only {unique_labels} class(es) found in DB. Training with available data, but results may be limited.")
    
    acc_svm, y_svm, y_pred_svm = train_svm(paths, labels)
    acc_cnn = train_cnn(paths, labels)
    acc_vit = train_vit(paths, labels)

    mean_accuracy = (acc_svm + acc_cnn + acc_vit) / 3.0

    stats = {
        "model_accuracies": [acc_svm, acc_cnn, acc_vit],
        "mean_accuracy": mean_accuracy,
        "precision": float(precision_score(y_svm, y_pred_svm, zero_division=0)),
        "recall": float(recall_score(y_svm, y_pred_svm, zero_division=0)),
        "f1": float(f1_score(y_svm, y_pred_svm, zero_division=0)),
        "n_good": n_good,
        "n_damaged": n_damaged,
        "note": "Trained on single class" if unique_labels < 2 else None
    }
    
    STATS_PATH.write_text(json.dumps(stats, indent=2))
    print(f"[INFO] Training complete. Mean accuracy: {mean_accuracy:.2%}")
    
    # Refresh cache
    load_models()
    return stats

# ── Inference ────────────────────────────────────────────────────────────────
_models_cache = {}

def load_models():
    svm_model = load_svm()
    cnn_model = load_cnn()
    vit_model = load_vit()
    
    if svm_model is None or cnn_model is None or vit_model is None:
        return False
        
    _models_cache["svm"] = svm_model
    _models_cache["cnn"] = cnn_model
    _models_cache["vit"] = vit_model
    return True

def classify_single_image(img_path: Path, img_url: str = None) -> dict:
    """
    Run classification on a single image using the ensemble model.
    
    This is the base classifier that runs SVM + CNN + ViT without augmentation.
    Used internally by the augmented classifier.
    
    Args:
        img_path: Path to the image file
        img_url: Optional original filename for tracking
        
    Returns:
        Dict with prediction, confidence, and per-model results
    """
    if not _models_cache:
        loaded = load_models()
        if not loaded:
            return None

    # SVM
    pred_svm, conf_svm = predict_svm(_models_cache["svm"], img_path)
    
    # CNN
    pred_cnn, conf_cnn = predict_cnn(_models_cache["cnn"], img_path)
    
    # ViT
    pred_vit, conf_vit = predict_vit(_models_cache["vit"], img_path)

    preds = [pred_svm, pred_cnn, pred_vit]
    good_count = preds.count("Good")
    final_pred = "Good" if good_count >= 2 else "Damaged"
    
    final_conf = (conf_svm + conf_cnn + conf_vit) / 3.0

    result = {
        "prediction": final_pred,
        "confidence": final_conf,
        "models": {
            "svm": {"prediction": pred_svm, "confidence": conf_svm},
            "cnn": {"prediction": pred_cnn, "confidence": conf_cnn},
            "vit": {"prediction": pred_vit, "confidence": conf_vit},
        },
        "original_filename": img_url or img_path.name,
    }

    # ── Damage localization (Grad-CAM) ───────────────────────────────────────
    # Only meaningful when the lens is flagged Damaged: highlight the region the
    # CNN used to decide "Damaged" so the operator can see the defect at a glance.
    if final_pred == "Damaged":
        try:
            from gradcam import generate_damage_overlay
            overlay = generate_damage_overlay(
                _models_cache["cnn"], img_path, predicted_class=1
            )
            if overlay is not None:
                HEATMAPS_DIR.mkdir(parents=True, exist_ok=True)
                heat_name = f"{img_path.stem}__heatmap.png"
                heat_path = HEATMAPS_DIR / heat_name
                overlay.save(heat_path)
                result["heatmap"] = heat_name
        except Exception as e:
            print(f"[WARN] damage overlay skipped for {img_path.name}: {e}")

    return result


def classify_image(img_path: Path, num_augmentations: int = 5, seed: Optional[int] = None) -> dict:
    """
    Classify an image using augmentation + majority voting.
    
    The image is augmented multiple times with different brightness, contrast,
    rotation, and noise variations. Each augmentation is classified by the
    ensemble model (SVM + CNN + ViT). The final prediction uses majority voting
    across all augmentations.
    
    SPECIAL RULE: When multiple images share the same group_id (via filename prefix),
    the final result is "Good" only if ALL images in the group are classified as Good.
    If ANY image in the group is classified as Damaged, the entire group is marked
    as Damaged.
    
    Args:
        img_path: Path to the image file
        num_augmentations: Number of augmented versions to generate
        seed: Optional random seed for reproducibility
        
    Returns:
        Dict with prediction, confidence, and per-model results
    """
    if not _models_cache:
        loaded = load_models()
        if not loaded:
            return None

    # Generate augmentations
    augmentations = get_augmentations(img_path, num_augs=num_augmentations, seed=seed)
    
    # Collect all predictions from augmentations
    all_predictions = []  # List of "Good"/"Damaged"
    all_results = []      # Full results for confidence calculation
    
    for aug_path, original_name in augmentations:
        result = classify_single_image(aug_path)
        if result is not None:
            result["original_filename"] = original_name
            all_results.append(result)
            all_predictions.append(result["prediction"])
    
    # Also classify the original image
    original_result = classify_single_image(img_path)
    if original_result is not None:
        all_results.append(original_result)
        all_predictions.append(original_result["prediction"])
    
    # Majority vote across all augmentations + original
    if not all_predictions:
        return {"prediction": "Error", "confidence": 0.0}
    
    good_count = all_predictions.count("Good")
    damaged_count = all_predictions.count("Damaged")
    
    final_pred = "Good" if good_count > damaged_count else "Damaged"
    
    # Final confidence is average of all confidences
    avg_conf = sum(r["confidence"] for r in all_results) / len(all_results)
    
    # Aggregate predictions and confidences for individual models
    svm_preds = [r["models"]["svm"]["prediction"] for r in all_results]
    svm_pred = "Good" if svm_preds.count("Good") >= svm_preds.count("Damaged") else "Damaged"
    svm_conf = sum(r["models"]["svm"]["confidence"] for r in all_results) / len(all_results)
    
    cnn_preds = [r["models"]["cnn"]["prediction"] for r in all_results]
    cnn_pred = "Good" if cnn_preds.count("Good") >= cnn_preds.count("Damaged") else "Damaged"
    cnn_conf = sum(r["models"]["cnn"]["confidence"] for r in all_results) / len(all_results)
    
    vit_preds = [r["models"]["vit"]["prediction"] for r in all_results]
    vit_pred = "Good" if vit_preds.count("Good") >= vit_preds.count("Damaged") else "Damaged"
    vit_conf = sum(r["models"]["vit"]["confidence"] for r in all_results) / len(all_results)
    
    result = {
        "prediction": final_pred,
        "confidence": avg_conf,
        "models": {
            "svm": {"prediction": svm_pred, "confidence": round(svm_conf, 4)},
            "cnn": {"prediction": cnn_pred, "confidence": round(cnn_conf, 4)},
            "vit": {"prediction": vit_pred, "confidence": round(vit_conf, 4)},
        },
        "original_filename": img_path.name,
    }
    
    # ── Damage localization (Grad-CAM) ───────────────────────────────────────
    if final_pred == "Damaged":
        try:
            from gradcam import generate_damage_overlay
            overlay = generate_damage_overlay(
                _models_cache["cnn"], img_path, predicted_class=1
            )
            if overlay is not None:
                HEATMAPS_DIR.mkdir(parents=True, exist_ok=True)
                heat_name = f"{img_path.stem}__heatmap.png"
                heat_path = HEATMAPS_DIR / heat_name
                overlay.save(heat_path)
                result["heatmap"] = heat_name
        except Exception as e:
            print(f"[WARN] damage overlay skipped for {img_path.name}: {e}")

    return result


def classify_group_with_consensus(images: List[Path], num_augmentations: int = 5, seed: Optional[int] = None) -> List[dict]:
    """
    Classify a group of related images with the consensus rule.
    
    If ANY image in the group is classified as Damaged, all images in the group
    are marked as Damaged. Only if ALL images are classified as Good will the
    group be considered Good.
    
    Args:
        images: List of image paths belonging to the same group
        num_augmentations: Number of augmentations per image
        seed: Optional random seed
        
    Returns:
        List of result dicts, one per image, all with the same prediction
    """
    individual_results = []
    
    for i, img_path in enumerate(images):
        # Use different seed for each image
        img_seed = (seed + i) if seed is not None else None
        result = classify_image(img_path, num_augmentations=num_augmentations, seed=img_seed)
        if result:
            individual_results.append(result)
    
    if not individual_results:
        return []
    
    # Consensus: Good only if ALL are Good
    all_good = all(r["prediction"] == "Good" for r in individual_results)
    group_prediction = "Good" if all_good else "Damaged"
    
    # Update all results with the group prediction
    for result in individual_results:
        if group_prediction == "Damaged":
            result["prediction"] = "Damaged"
            # Recalculate confidence as average of all group members
            result["confidence"] = sum(r["confidence"] for r in individual_results) / len(individual_results)
        # Remove heatmap if marked as Good (clean up any stray heatmaps)
        if group_prediction == "Good" and "heatmap" in result:
            del result["heatmap"]
    
    return individual_results
