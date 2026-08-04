import json
from pathlib import Path
from sklearn.metrics import precision_score, recall_score, f1_score

from classifier_utils import load_image_paths, STATS_PATH, HEATMAPS_DIR
from classifier_svm import train_svm, load_svm, predict_svm
from classifier_cnn import train_cnn, load_cnn, predict_cnn
from classifier_vit import train_vit, load_vit, predict_vit

# ── Training & Evaluation ────────────────────────────────────────────────────
def train_and_evaluate():
    paths, labels = load_image_paths()
    if not paths:
        raise ValueError("No images found in the DB folder. Please upload images first.")
    
    import numpy as np
    if len(np.unique(labels)) < 2:
        raise ValueError("Need images from BOTH classes to train. Add images to the missing folder and retrain.")

    n_good = labels.count(0)
    n_damaged = labels.count(1)
    
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

def classify_image(img_path: Path):
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
