import os
import json
import numpy as np
from pathlib import Path
from PIL import Image
import joblib
from skimage.feature import hog
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    confusion_matrix, precision_score, recall_score, f1_score, accuracy_score
)

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
DB_DIR      = BASE_DIR.parent.parent / "DB"   # OptyLab/DB
GOOD_DIR    = DB_DIR / "Good"
DAMAGED_DIR = DB_DIR / "Damaged"
MODEL_DIR   = BASE_DIR / "model"
MODEL_PATH  = MODEL_DIR / "classifier.pkl"
STATS_PATH  = MODEL_DIR / "stats.json"

IMG_SIZE    = (128, 128)   # resize target before HOG
N_FOLDS     = 5


# ── Feature extraction ───────────────────────────────────────────────────────
def extract_hog(img_path: Path) -> np.ndarray | None:
    """Return HOG feature vector for one image, or None if the file is unreadable."""
    try:
        img = Image.open(img_path).convert("L").resize(IMG_SIZE)
        arr = np.array(img)
        features = hog(
            arr,
            orientations=9,
            pixels_per_cell=(16, 16),
            cells_per_block=(2, 2),
            block_norm="L2-Hys",
        )
        return features
    except Exception as e:
        print(f"[WARN] Could not process {img_path.name}: {e}")
        return None


def load_dataset():
    """Load Good + Damaged images and return (X, y, n_good, n_damaged)."""
    VALID = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
    X, y = [], []

    for folder, label, name in [
        (GOOD_DIR, 0, "Good"),
        (DAMAGED_DIR, 1, "Damaged"),
    ]:
        if not folder.exists():
            print(f"[WARN] {name} folder not found: {folder}")
            continue
        files = [f for f in folder.iterdir() if f.suffix.lower() in VALID]
        print(f"[INFO] Found {len(files)} {name} images")
        for f in files:
            feat = extract_hog(f)
            if feat is not None:
                X.append(feat)
                y.append(label)

    n_good    = y.count(0)
    n_damaged = y.count(1)
    return np.array(X), np.array(y), n_good, n_damaged


# ── Training ─────────────────────────────────────────────────────────────────
def train_and_evaluate() -> dict:
    """
    Train HOG+SVM with 5-fold stratified CV.
    Returns a stats dict and saves model + stats to disk.
    """
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    X, y, n_good, n_damaged = load_dataset()

    if len(np.unique(y)) < 2:
        raise ValueError(
            f"Need images from BOTH classes to train. "
            f"Currently: {n_good} Good, {n_damaged} Damaged. "
            f"Add images to the missing folder and retrain."
        )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("svm",    SVC(kernel="rbf", probability=True, C=5.0, gamma="scale")),
    ])

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=42)

    cv_results = cross_validate(
        pipeline, X, y,
        cv=skf,
        scoring=["accuracy", "precision", "recall", "f1"],
        return_estimator=False,
    )

    fold_accuracies = cv_results["test_accuracy"].tolist()
    mean_accuracy   = float(np.mean(fold_accuracies))
    precision       = float(np.mean(cv_results["test_precision"]))
    recall          = float(np.mean(cv_results["test_recall"]))
    f1              = float(np.mean(cv_results["test_f1"]))

    # Fit on full dataset for deployment
    pipeline.fit(X, y)
    joblib.dump(pipeline, MODEL_PATH)

    # Confusion matrix on full training data (indicative)
    y_pred = pipeline.predict(X)
    cm = confusion_matrix(y, y_pred).tolist()

    stats = {
        "fold_accuracies": fold_accuracies,
        "mean_accuracy":   mean_accuracy,
        "precision":       precision,
        "recall":          recall,
        "f1":              f1,
        "confusion_matrix": cm,
        "n_good":          n_good,
        "n_damaged":       n_damaged,
    }
    STATS_PATH.write_text(json.dumps(stats, indent=2))
    print(f"[INFO] Training complete. Mean accuracy: {mean_accuracy:.2%}")
    return stats


# ── Inference ────────────────────────────────────────────────────────────────
def load_model():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def classify_image(img_path: Path, model) -> dict:
    """Run the model on one image. Returns prediction + confidence."""
    feat = extract_hog(img_path)
    if feat is None:
        return {"prediction": "Error", "confidence": 0.0}
    feat_2d = feat.reshape(1, -1)
    label_idx = model.predict(feat_2d)[0]
    proba     = model.predict_proba(feat_2d)[0]
    label     = "Good" if label_idx == 0 else "Damaged"
    confidence = float(proba[label_idx])
    return {"prediction": label, "confidence": confidence}
