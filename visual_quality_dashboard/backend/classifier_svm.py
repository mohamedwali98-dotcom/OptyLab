import joblib
import numpy as np
from pathlib import Path
from PIL import Image
from skimage.feature import hog
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import GridSearchCV, GroupKFold, StratifiedKFold
from classifier_utils import MODEL_DIR

MODEL_PATH_SVM = MODEL_DIR / "classifier_svm.pkl"
# High precision resizing for eye lenses (224x224)
IMG_SIZE = (224, 224)

def extract_hog(img_path: Path) -> np.ndarray | None:
    try:
        # Using BICUBIC interpolation for high precision resizing
        img = Image.open(img_path).convert("L").resize(IMG_SIZE, resample=Image.BICUBIC)
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

def _extract_features(paths, labels, groups=None):
    """HOG-encode every path, dropping unreadable images. `groups` (if given)
    is filtered in lockstep so it stays aligned with the returned X/y for a
    grouped cross-validation split."""
    groups_in = groups if groups is not None else [None] * len(paths)
    X, y, g = [], [], []
    for p, l, gi in zip(paths, labels, groups_in):
        feat = extract_hog(p)
        if feat is not None:
            X.append(feat)
            y.append(l)
            g.append(gi)
    return np.array(X), np.array(y), g

def train_svm(paths, labels, groups=None):
    """
    Fit HOG + calibrated RBF-SVC on the given training split.

    C/gamma are chosen via a small cross-validated grid search (grouped by
    raw source image when `groups` is given) instead of a fixed C=5.0, which
    was overfitting this small dataset. Returns the fitted pipeline; weights
    are also saved to disk as before.
    """
    print("[INFO] Training SVM...")
    X, y, g = _extract_features(paths, labels, groups)
    if len(y) == 0:
        raise ValueError("No valid images to train the SVM on.")

    unique, counts = np.unique(y, return_counts=True)
    n_splits = min(3, counts.min()) if len(unique) > 1 else 0

    best_params = {"C": 5.0, "gamma": "scale"}  # fallback if CV isn't possible
    if n_splits >= 2:
        base = Pipeline([("scaler", StandardScaler()), ("svm", SVC(kernel="rbf"))])
        grid = {"svm__C": [0.5, 1.0, 2.0, 5.0], "svm__gamma": ["scale", "auto"]}
        if groups is not None and len(set(g)) >= n_splits:
            cv = list(GroupKFold(n_splits=n_splits).split(X, y, g))
        else:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=13)
        search = GridSearchCV(base, grid, cv=cv, scoring="accuracy")
        search.fit(X, y)
        best_params = {"C": search.best_params_["svm__C"], "gamma": search.best_params_["svm__gamma"]}
        print(f"[INFO] SVM grid search best params: {best_params}")
    else:
        print("[INFO] Not enough samples/classes to grid-search; using default SVM params.")

    # CalibratedClassifierCV instead of deprecated probability=True — gives
    # probability estimates while being forward-compatible.
    svm_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("svm", CalibratedClassifierCV(SVC(kernel="rbf", **best_params), ensemble=False)),
    ])
    svm_pipeline.fit(X, y)
    joblib.dump(svm_pipeline, MODEL_PATH_SVM)
    return svm_pipeline

def load_svm():
    if not MODEL_PATH_SVM.exists():
        return None
    return joblib.load(MODEL_PATH_SVM)

def proba_svm(model, paths) -> np.ndarray:
    """Batch inference: (n, 2) array of [P(Good), P(Damaged)]. Unreadable
    images fall back to a neutral 0.5/0.5 rather than dropping the row, so the
    output stays aligned with `paths` for the caller's metric computation."""
    out = np.full((len(paths), 2), 0.5)
    feats, idx = [], []
    for i, p in enumerate(paths):
        feat = extract_hog(p)
        if feat is not None:
            feats.append(feat)
            idx.append(i)
    if feats:
        proba = model.predict_proba(np.array(feats))
        for j, i in enumerate(idx):
            out[i] = proba[j]
    return out

def predict_svm(model, img_path: Path):
    feat = extract_hog(img_path)
    if feat is None:
        return {"prediction": "Error", "confidence": 0.0}
    feat_2d = feat.reshape(1, -1)
    label_idx = model.predict(feat_2d)[0]
    proba = model.predict_proba(feat_2d)[0]
    conf = float(proba[label_idx])
    pred = "Good" if label_idx == 0 else "Damaged"
    return pred, conf
