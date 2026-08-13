import joblib
import numpy as np
from pathlib import Path
from PIL import Image
from skimage.feature import hog
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score
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

def train_svm(paths, labels):
    print("[INFO] Training SVM...")
    X_svm = []
    y_svm = []
    for p, l in zip(paths, labels):
        feat = extract_hog(p)
        if feat is not None:
            X_svm.append(feat)
            y_svm.append(l)
    X_svm = np.array(X_svm)
    y_svm = np.array(y_svm)

    # Use CalibratedClassifierCV instead of deprecated probability=True
    # This provides probability estimates while being forward-compatible
    svm_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("svm", CalibratedClassifierCV(
            SVC(kernel="rbf", C=5.0, gamma="scale"),
            ensemble=False
        )),
    ])
    svm_pipeline.fit(X_svm, y_svm)
    joblib.dump(svm_pipeline, MODEL_PATH_SVM)
    
    y_pred_svm = svm_pipeline.predict(X_svm)
    acc = accuracy_score(y_svm, y_pred_svm)
    return acc, y_svm, y_pred_svm

def load_svm():
    if not MODEL_PATH_SVM.exists():
        return None
    return joblib.load(MODEL_PATH_SVM)

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
