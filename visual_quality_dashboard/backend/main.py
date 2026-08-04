"""
main.py
=======
FastAPI backend for the OptyLab Visual Quality Inspector.

Start with:
    uvicorn main:app --reload --port 8000
"""

import json
import os
import uuid
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# Load environment configuration from a local .env file (if present) so you can
# configure things like the admin-email seed WITHOUT exporting vars in the shell.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass  # python-dotenv is optional; env vars still work if set directly.

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from classifier import train_and_evaluate, load_models, classify_image
from classifier_utils import STATS_PATH, MODEL_DIR, GOOD_DIR, DAMAGED_DIR
import auth
from auth import (  # noqa: F401  (re-exported names referenced by endpoints)
    init_db, create_user, authenticate, get_user_by_id, change_password,
    is_admin_allowed, list_admin_access, grant_admin_access,
    revoke_admin_access, record_login, get_history, current_user,
    client_ip, normalize_email,
)

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="OptyLab API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
UPLOADS_DIR  = BASE_DIR / "uploads"
RESULTS_FILE = BASE_DIR / "results.json"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ── Auth bootstrap ─────────────────────────────────────────────────────────────
# Create the auth DB / tables and seed the initial admin(s) if none exist yet.
# Set OPTYLAB_ADMIN_EMAILS (comma-separated) to pre-authorise specific emails;
# otherwise the FIRST registered account automatically becomes an admin so the
# "sheet" is never locked out.
init_db()
_seed = os.environ.get("OPTYLAB_ADMIN_EMAILS")
if _seed:
    for _e in [e.strip() for e in _seed.split(",") if e.strip()]:
        try:
            grant_admin_access(auth.normalize_email(_e), "env-seed")
        except Exception:
            pass

# ── Helpers ──────────────────────────────────────────────────────────────────
def read_results() -> list:
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return []

def write_results(data: list):
    RESULTS_FILE.write_text(json.dumps(data, indent=2))


# ── Auth request models ────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class AccessRequest(BaseModel):
    email: str


# ── Auth dependency ─────────────────────────────────────────────────────────────
def require_user(request: Request) -> dict:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return user


def require_admin_access(request: Request) -> dict:
    """User must be logged in AND on the admin-access list."""
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if not is_admin_allowed(user["email"]):
        raise HTTPException(status_code=403, detail="Your email is not granted admin access.")
    return user


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/auth/register")
def register(req: RegisterRequest, request: Request):
    """Create an account. The very first account is auto-granted admin access
    so the access-control sheet is never locked out."""
    try:
        user = create_user(req.email, req.name, req.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # First registered user becomes an admin automatically.
    if not list_admin_access():
        grant_admin_access(user["email"], "first-user")

    token = auth.create_token(user["id"], user["email"])
    auth.record_login(user["id"], user["email"], client_ip(request), "register")
    return {
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "admin_access": is_admin_allowed(user["email"]),
    }


@app.post("/auth/login")
def login(req: LoginRequest, request: Request):
    user = authenticate(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = auth.create_token(user["id"], user["email"])
    auth.record_login(user["id"], user["email"], client_ip(request), "login")
    return {
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "admin_access": is_admin_allowed(user["email"]),
    }


@app.get("/auth/me")
def me(user: dict = Depends(require_user)):
    return {
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "admin_access": is_admin_allowed(user["email"]),
    }


@app.post("/auth/change-password")
def change_pw(req: ChangePasswordRequest, user: dict = Depends(require_user)):
    try:
        change_password(user["id"], req.old_password, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    auth.record_login(user["id"], user["email"], None, "change-password")
    return {"message": "Password updated successfully."}


@app.get("/auth/history")
def history(user: dict = Depends(require_user)):
    """Last 20 login/activity entries for the current user."""
    return {"history": get_history(user["id"], limit=20)}


@app.get("/auth/admin-access")
def get_access(user: dict = Depends(require_admin_access)):
    """List every email allowed to view the Admin tab (the 'sheet')."""
    return {"emails": list_admin_access()}


@app.post("/auth/admin-access")
def add_access(req: AccessRequest, user: dict = Depends(require_admin_access)):
    try:
        entry = grant_admin_access(normalize_email(req.email), user["email"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"{entry['email']} granted admin access.", "email": entry["email"]}


@app.delete("/auth/admin-access")
def del_access(req: AccessRequest, user: dict = Depends(require_admin_access)):
    revoke_admin_access(normalize_email(req.email))
    return {"message": f"{normalize_email(req.email)} removed from admin access."}



@app.get("/")
def root():
    return {"message": "OptyLab API running"}


@app.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    group_id: str = Form(None)
):
    """Accept PNG images from the frontend and save them to the upload queue."""
    saved = []
    for f in files:
        if not f.content_type.startswith("image/"):
            continue
        safe_name = Path(f.filename).name
        if group_id:
            safe_name = f"{group_id}___{safe_name}"
            
        dest = UPLOADS_DIR / safe_name
        # If a file with the same name exists, suffix with a short uuid
        if dest.exists():
            stem   = Path(safe_name).stem
            suffix = Path(safe_name).suffix
            dest = UPLOADS_DIR / f"{stem}_{uuid.uuid4().hex[:6]}{suffix}"
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(dest.name)
    return {"message": f"Uploaded {len(saved)} file(s)", "files": saved}


@app.get("/queue")
def get_queue():
    """List files waiting for classification."""
    classified = {r["filename"] for r in read_results()}
    pending = [
        {"filename": f.name, "status": "classified" if f.name in classified else "queued"}
        for f in sorted(UPLOADS_DIR.iterdir())
        if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
    ]
    return {"queue": pending}


def _image_derived_confidence(img_path: Path) -> tuple[str, float, float, float]:
    """
    Compute real, image-derived signals to estimate quality confidence.
    Used as a fallback when no trained model is available.

    Returns (prediction, conf_svm_proxy, conf_cnn_proxy, conf_vit_proxy).

    The three "model" scores are computed from distinct but complementary
    low-level image features so that each column in the dashboard reflects
    something genuinely different about the image:

      SVM-proxy  → HOG feature energy / variance  (texture richness)
      CNN-proxy  → Normalised pixel std-dev        (contrast / sharpness)
      ViT-proxy  → Local block entropy mean        (structural complexity)
    """
    import numpy as np
    from PIL import Image

    try:
        # ── Load as greyscale, resize to 128×128 for speed ────────────────
        img = Image.open(img_path).convert("L").resize((128, 128), Image.BICUBIC)
        arr = np.array(img, dtype=np.float32) / 255.0      # [0, 1]

        # ── Signal 1 (SVM proxy): HOG-energy variance ──────────────────────
        # Compute simple gradient magnitudes as a lightweight HOG proxy
        gy = np.abs(np.diff(arr, axis=0))  # vertical gradients
        gx = np.abs(np.diff(arr, axis=1))  # horizontal gradients
        grad_mag = (gy[:, :-1] + gx[:-1, :]) / 2.0
        hog_energy = float(np.var(grad_mag))
        # Map variance to [0.50, 0.99] — higher texture variance → higher confidence
        conf_svm = round(0.50 + min(hog_energy * 80.0, 0.49), 4)

        # ── Signal 2 (CNN proxy): normalised global std-dev ─────────────────
        std_dev = float(np.std(arr))
        # Images with rich contrast (std ~0.2-0.4) are clearer → higher confidence
        # Very uniform (std≈0) or overexposed (std≈0.5+) score lower
        peak = 0.25   # expected std for a well-exposed image
        raw_cnn = 1.0 - abs(std_dev - peak) / peak
        conf_cnn = round(max(0.50, min(raw_cnn * 0.49 + 0.50, 0.99)), 4)

        # ── Signal 3 (ViT proxy): mean local block entropy ─────────────────
        block = 16
        entropies = []
        for r in range(0, 128 - block + 1, block):
            for c in range(0, 128 - block + 1, block):
                patch = arr[r:r + block, c:c + block].ravel()
                # Histogram-based entropy on 16 bins
                hist, _ = np.histogram(patch, bins=16, range=(0, 1))
                hist = hist[hist > 0].astype(np.float32)
                hist /= hist.sum()
                entropies.append(-float(np.sum(hist * np.log2(hist))))
        mean_entropy = float(np.mean(entropies)) if entropies else 2.0
        # Max possible entropy with 16 bins ≈ 4.0; good images usually 2.5-3.5
        conf_vit = round(0.50 + min(mean_entropy / 8.0, 0.49), 4)

        # ── Ensemble decision ──────────────────────────────────────────────
        avg_conf = (conf_svm + conf_cnn + conf_vit) / 3.0
        # Heuristic: high contrast + high texture → Good; flat / very noisy → Damaged
        prediction = "Good" if avg_conf >= 0.65 else "Damaged"

        return prediction, conf_svm, conf_cnn, conf_vit

    except Exception as exc:
        print(f"[WARN] _image_derived_confidence failed for {img_path.name}: {exc}")
        # Last resort: fixed mid-range values so at least the numbers are not random
        return "Good", 0.72, 0.68, 0.70


def _mock_classify(img_path: Path) -> dict:
    """
    Fallback classifier used when no trained model is available.
    Produces confidence values derived from real image features
    (texture energy, contrast, local entropy) — NOT random numbers.
    """
    prediction, conf_svm, conf_cnn, conf_vit = _image_derived_confidence(img_path)

    # Each "model" gets its own image-derived score
    # All three agree with the ensemble prediction for consistency
    pred_svm = pred_cnn = pred_vit = prediction
    avg_conf = round((conf_svm + conf_cnn + conf_vit) / 3.0, 4)

    return {
        "prediction": prediction,
        "confidence": avg_conf,
        "models": {
            "svm": {"prediction": pred_svm, "confidence": conf_svm},
            "cnn": {"prediction": pred_cnn, "confidence": conf_cnn},
            "vit": {"prediction": pred_vit, "confidence": conf_vit},
        }
    }


@app.post("/classify")
def classify_all():
    """
    Run classification on every uploaded image and store results.
    - If a trained model exists  → uses HOG+SVM (real predictions).
    - If no model is trained yet → falls back to random mock labels so
      newly uploaded images always appear in the Results tab.
    """
    VALID = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
    files = [f for f in UPLOADS_DIR.iterdir() if f.is_file() and f.suffix.lower() in VALID]

    if not files:
        raise HTTPException(status_code=400, detail="No uploaded images to classify.")

    use_model = load_models()

    existing = {r["filename"]: r for r in read_results()}

    new_results = []
    for img_path in sorted(files):
        if img_path.name in existing:
            new_results.append(existing[img_path.name])
            continue
            
        group_id = None
        if "___" in img_path.name:
            group_id = img_path.name.split("___", 1)[0]
            
        result = classify_image(img_path) if use_model else _mock_classify(img_path)
        entry = {
            "id":         f"OPY-{uuid.uuid4().hex[:6].upper()}",
            "filename":   img_path.name,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "prediction": result["prediction"],
            "confidence": result["confidence"],
            "models": result.get("models", {}),
            "thumbnail":  True,
            "group_id":   group_id,
        }
        new_results.append(entry)

    write_results(new_results)
    mode = "model" if use_model else "mock (no trained model)"
    return {
        "message": f"Classified {len(new_results)} image(s) using {mode}",
        "count": len(new_results),
        "mode": "model" if use_model else "mock",
    }


@app.get("/results")
def get_results():
    """Return all classification results, automatically cleaning up any missing files."""
    results = read_results()
    valid_results = []
    changed = False
    
    for r in results:
        path = UPLOADS_DIR / r["filename"]
        if path.exists():
            valid_results.append(r)
        else:
            changed = True
            
    if changed:
        write_results(valid_results)
        
    return {"results": valid_results}


@app.get("/thumbnail/{filename}")
def get_thumbnail(filename: str):
    """Serve uploaded image as thumbnail."""
    safe = Path(filename).name
    path = UPLOADS_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path))


@app.delete("/clear-uploads")
def clear_uploads(user: dict = Depends(require_admin_access)):
    """Delete all files in the uploads folder and reset the results cache."""
    deleted = 0
    for f in UPLOADS_DIR.iterdir():
        if f.is_file():
            f.unlink()
            deleted += 1
    # Also clear results so they don't reference deleted files
    write_results([])
    return {"message": f"Cleared {deleted} file(s) from the upload queue."}


@app.delete("/upload/{filename}")
def delete_upload(filename: str):
    """Delete a single file from the uploads folder."""
    safe = Path(filename).name
    path = UPLOADS_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    path.unlink()
    
    # Also remove it from results.json if it was classified
    results = read_results()
    new_results = [r for r in results if r["filename"] != safe]
    if len(results) != len(new_results):
        write_results(new_results)
        
    return {"message": f"Deleted {safe}"}


@app.post("/train")
def train_model(user: dict = Depends(require_admin_access)):
    """Train/retrain the classifier using the DB images."""
    try:
        stats = train_and_evaluate()
        return {"message": "Training complete", "stats": stats}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/model-stats")
def model_stats():
    """Return the last training statistics."""
    if not STATS_PATH.exists():
        raise HTTPException(status_code=404, detail="No stats found. Train the model first.")
    return json.loads(STATS_PATH.read_text())


class CorrectionRequest(BaseModel):
    filename: str
    corrected_label: str


@app.post("/correct-prediction")
def correct_prediction(req: CorrectionRequest, user: dict = Depends(require_admin_access)):
    """
    Correct a wrong classification:
    1. Copy the image from UPLOADS_DIR to DB/Good or DB/Damaged depending on the corrected label.
    2. Update its prediction in results.json.
    """
    # 1. Verify file exists
    src_file = UPLOADS_DIR / req.filename
    if not src_file.exists():
        raise HTTPException(status_code=404, detail="Original uploaded file not found.")

    # 2. Get destination directory
    if req.corrected_label == "Good":
        dest_dir = GOOD_DIR
    elif req.corrected_label == "Damaged":
        dest_dir = DAMAGED_DIR
    else:
        raise HTTPException(status_code=400, detail="Invalid corrected label. Must be 'Good' or 'Damaged'.")

    # Ensure destination directory exists
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / req.filename

    # Copy the file to DB folder
    try:
        shutil.copy2(src_file, dest_file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to copy file to DB: {str(e)}")

    # 3. Update results.json
    results = read_results()
    updated = False
    for r in results:
        if r["filename"] == req.filename:
            r["prediction"] = req.corrected_label
            r["confidence"] = 1.0  # Mark as 100% confidence/verified
            r["corrected"] = True  # Custom field to indicate override
            updated = True
            break
    
    if not updated:
        # If not found in results, create a new entry
        entry = {
            "id": f"OPY-{uuid.uuid4().hex[:6].upper()}",
            "filename": req.filename,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prediction": req.corrected_label,
            "confidence": 1.0,
            "thumbnail": True,
            "corrected": True
        }
        results.append(entry)
    
    write_results(results)
    return {"message": f"Successfully corrected {req.filename} to {req.corrected_label}"}


@app.get("/upload-stats")
def get_upload_stats():
    """Return count of uploaded files and stats details."""
    files = [f for f in UPLOADS_DIR.iterdir() if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}]
    results = read_results()
    return {
        "total_uploaded": len(files),
        "total_classified": len(results)
    }
