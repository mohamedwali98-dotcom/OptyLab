import json
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit

from classifier_utils import load_image_paths_with_groups, STATS_PATH, HEATMAPS_DIR
from classifier_svm import train_svm, load_svm, predict_svm, proba_svm
from classifier_cnn import train_cnn, load_cnn, predict_cnn, proba_cnn
from classifier_vit import train_vit, load_vit, predict_vit, proba_vit
from augmentation import get_augmentations, parse_group_id

# ── Splitting ─────────────────────────────────────────────────────────────────
def _grouped_split(paths, labels, groups, test_fraction=0.2, seed=13):
    """
    Split indices into (train_idx, test_idx) grouped by raw source image, so
    augmented siblings of one photo never straddle the boundary (a naive
    random split would leak near-duplicates between train and test and make
    the held-out accuracy meaningless). Stratifies by label when there are
    enough distinct groups to do so; falls back to a plain grouped split
    otherwise.
    """
    n_groups = len(set(groups))
    if n_groups < 2:
        # Not enough distinct source images to hold anything out. Train on
        # everything and evaluate on that same data as a best effort — the
        # "eval" field written to stats.json makes this explicit so the
        # number is never mistaken for a real held-out accuracy.
        idx = list(range(len(paths)))
        return idx, idx

    y = np.array(labels)
    n_splits = max(2, min(5, n_groups, round(1 / test_fraction)))
    try:
        from sklearn.model_selection import StratifiedGroupKFold
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        train_idx, test_idx = next(splitter.split(paths, y, groups))
    except (ImportError, ValueError):
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_fraction, random_state=seed)
        train_idx, test_idx = next(splitter.split(paths, y, groups))
    return list(train_idx), list(test_idx)


# ── Training & Evaluation ────────────────────────────────────────────────────
def train_and_evaluate():
    paths, labels, groups = load_image_paths_with_groups()
    if not paths:
        raise ValueError("No images found in the DB folder. Please upload images first.")

    n_good = labels.count(0)
    n_damaged = labels.count(1)
    unique_labels = len(set(labels))

    # Log warning if only one class available (training will still work but results may be limited)
    if unique_labels < 2:
        print(f"[WARN] Only {unique_labels} class(es) found in DB. Training with available data, but results may be limited.")

    # ── Held-out test split, grouped by raw source image ────────────────────
    trainval_idx, test_idx = _grouped_split(paths, labels, groups, test_fraction=0.2)
    trainval_paths  = [paths[i]  for i in trainval_idx]
    trainval_labels = [labels[i] for i in trainval_idx]
    trainval_groups = [groups[i] for i in trainval_idx]
    test_paths  = [paths[i]  for i in test_idx]
    test_labels = [labels[i] for i in test_idx]

    leaked_groups = set(trainval_groups) & set(groups[i] for i in test_idx)
    if trainval_idx != test_idx:
        assert not leaked_groups, f"Data leakage: groups on both sides of split: {leaked_groups}"

    # ── Inner train/val split for CNN/ViT early stopping, also grouped ──────
    train_idx, val_idx = _grouped_split(trainval_paths, trainval_labels, trainval_groups, test_fraction=0.15)
    train_paths  = [trainval_paths[i]  for i in train_idx]
    train_labels = [trainval_labels[i] for i in train_idx]
    train_groups = [trainval_groups[i] for i in train_idx]
    val_paths  = [trainval_paths[i]  for i in val_idx]
    val_labels = [trainval_labels[i] for i in val_idx]

    print(f"[INFO] Split -> train: {len(train_paths)}  val: {len(val_paths)}  "
          f"test: {len(test_paths)}  (grouped by {len(set(groups))} raw source images)")

    # ── Train each model on train only, validate/early-stop on val ──────────
    svm_model = train_svm(train_paths, train_labels, groups=train_groups)
    cnn_model = train_cnn(train_paths, train_labels, val_paths, val_labels)
    vit_model = train_vit(train_paths, train_labels, val_paths, val_labels)

    # ── Evaluate everything on the untouched held-out test set ──────────────
    y_test = np.array(test_labels)
    proba_s = proba_svm(svm_model, test_paths)
    proba_c = proba_cnn(cnn_model, test_paths)
    proba_v = proba_vit(vit_model, test_paths)

    pred_s = proba_s.argmax(axis=1)
    pred_c = proba_c.argmax(axis=1)
    pred_v = proba_v.argmax(axis=1)

    acc_svm = float(accuracy_score(y_test, pred_s))
    acc_cnn = float(accuracy_score(y_test, pred_c))
    acc_vit = float(accuracy_score(y_test, pred_v))

    # Accuracy-weighted soft vote: a model that tested weaker gets less say.
    # Falls back to an equal-weight average if every model scored 0 (e.g. a
    # degenerate single-image test set).
    raw_weights = np.array([acc_svm, acc_cnn, acc_vit])
    weights = raw_weights / raw_weights.sum() if raw_weights.sum() > 0 else np.full(3, 1 / 3)

    ensemble_proba_damaged = weights[0] * proba_s[:, 1] + weights[1] * proba_c[:, 1] + weights[2] * proba_v[:, 1]
    ensemble_pred = (ensemble_proba_damaged >= 0.5).astype(int)

    mean_accuracy = (acc_svm + acc_cnn + acc_vit) / 3.0
    ensemble_accuracy = float(accuracy_score(y_test, ensemble_pred))
    cm = confusion_matrix(y_test, ensemble_pred, labels=[0, 1]).tolist()

    stats = {
        "eval": "held-out grouped test split" if trainval_idx != test_idx else "trained on full data (too few source images to hold out a test set)",
        "model_accuracies": [acc_svm, acc_cnn, acc_vit],
        "ensemble_weights": weights.tolist(),
        "mean_accuracy": mean_accuracy,
        "ensemble_accuracy": ensemble_accuracy,
        "precision": float(precision_score(y_test, ensemble_pred, zero_division=0)),
        "recall": float(recall_score(y_test, ensemble_pred, zero_division=0)),
        "f1": float(f1_score(y_test, ensemble_pred, zero_division=0)),
        "confusion_matrix": cm,
        "n_good": n_good,
        "n_damaged": n_damaged,
        "n_train": len(train_paths),
        "n_val": len(val_paths),
        "n_test": len(test_paths),
        "note": "Trained on single class" if unique_labels < 2 else None
    }

    STATS_PATH.write_text(json.dumps(stats, indent=2))
    print(f"[INFO] Training complete. Ensemble held-out accuracy: {ensemble_accuracy:.2%} "
          f"(SVM {acc_svm:.2%} / CNN {acc_cnn:.2%} / ViT {acc_vit:.2%})")

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

def _ensemble_weights() -> Tuple[float, float, float]:
    """Per-model vote weights from the last held-out evaluation
    (stats.json["ensemble_weights"]), falling back to an equal 1/3 split if
    no stats have been written yet."""
    if STATS_PATH.exists():
        try:
            stats = json.loads(STATS_PATH.read_text())
            w = stats.get("ensemble_weights")
            if w and len(w) == 3 and sum(w) > 0:
                return tuple(w)
        except Exception:
            pass
    return (1 / 3, 1 / 3, 1 / 3)

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

    # Soft, accuracy-weighted vote: each model contributes its own confidence
    # in "Damaged" (not just a +1/-1 vote), scaled by how well that model
    # actually did on the last held-out test set. This keeps a model that
    # tests weak (e.g. an under-trained ViT) from being able to overrule two
    # confident, accurate models the way a flat 2-of-3 majority vote could.
    w_svm, w_cnn, w_vit = _ensemble_weights()
    p_damaged_svm = conf_svm if pred_svm == "Damaged" else (1.0 - conf_svm)
    p_damaged_cnn = conf_cnn if pred_cnn == "Damaged" else (1.0 - conf_cnn)
    p_damaged_vit = conf_vit if pred_vit == "Damaged" else (1.0 - conf_vit)
    p_damaged = w_svm * p_damaged_svm + w_cnn * p_damaged_cnn + w_vit * p_damaged_vit

    final_pred = "Damaged" if p_damaged >= 0.5 else "Good"
    final_conf = p_damaged if final_pred == "Damaged" else (1.0 - p_damaged)

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
