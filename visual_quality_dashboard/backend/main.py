"""
Start with:
    uvicorn main:app --reload --port 8000
"""

import json
import os
import uuid
import random
import shutil
import asyncio
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
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from classifier import train_and_evaluate, load_models, classify_image, classify_group_with_consensus
from classifier_utils import STATS_PATH, MODEL_DIR, GOOD_DIR, DAMAGED_DIR, HEATMAPS_DIR, RAW_GOOD_DIR, RAW_DAMAGED_DIR
from augmentation import parse_group_id
import auth
from auth import (  # noqa: F401  (re-exported names referenced by endpoints)
    init_db, create_user, authenticate, get_user_by_id, change_password,
    is_admin_allowed, list_admin_access, grant_admin_access,
    revoke_admin_access, record_login, get_history, current_user,
    record_process, get_processed,
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
HEATMAPS_DIR.mkdir(parents=True, exist_ok=True)

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


@app.get("/auth/processed")
def processed(user: dict = Depends(require_user)):
    """Last 20 images processed (classified) by the current user."""
    return {"processed": get_processed(user["id"], limit=20)}


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
        if f.is_file()
        and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
        # Damage-localization overlays (`<stem>__heatmap.png`) are NOT queue
        # items - they belong in the separate heatmaps/ folder, so exclude them.
        and not f.name.endswith("__heatmap.png")
    ]
    return {"queue": pending}


@app.post("/classify")
def classify_all(request: Request):
    """
    Run classification on every uploaded image and store results.
    - Requires trained models (uses augmentation + ensemble voting).
    - If no model is trained yet, raises HTTP 400 error.

    Images are grouped by their prefix (before "___"). For grouped images, the
    consensus rule applies: if ANY image in a group is classified as Damaged,
    ALL images in that group are marked as Damaged. Only if ALL images are 
    classified as Good will the entire group be considered Good.

    If the caller is authenticated, each newly-classified image is recorded
    under that user's account so they can review their own processing history.
    """
    VALID = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
    files = [
        f for f in UPLOADS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in VALID
        and not f.name.endswith("__heatmap.png")
    ]

    if not files:
        raise HTTPException(status_code=400, detail="No uploaded images to classify.")

    use_model = load_models()
    if not use_model:
        raise HTTPException(
            status_code=400,
            detail="Ensemble models are not trained yet. Please go to the Admin page and click 'Retrain Model' first."
        )

    # Optional attribution: the user who triggered the run (None if anon).
    actor = current_user(request)
    actor_id = actor["id"] if actor else None
    actor_email = actor["email"] if actor else None

    existing = {r["filename"]: r for r in read_results()}

    # Group images by their group_id (prefix before "___")
    groups = {}
    for img_path in files:
        if img_path.name in existing:
            continue  # Skip already-classified images
        group_id = parse_group_id(img_path.name)
        if group_id is None:
            group_id = img_path.name  # No group, use filename as group_id
        if group_id not in groups:
            groups[group_id] = []
        groups[group_id].append(img_path)

    new_results = []
    
    # Process each group with consensus voting
    for group_id, group_files in groups.items():
        # Get group_id for result entries
        actual_group_id = None if len(group_files) == 1 and "___" not in group_files[0].name else group_id
        
        if len(group_files) == 1:
            # Single image with no group prefix - classify individually
            img_path = group_files[0]
            result = classify_image(img_path)
            
            entry = {
                "id":         f"OPY-{uuid.uuid4().hex[:6].upper()}",
                "filename":   img_path.name,
                "timestamp":  datetime.now(timezone.utc).isoformat(),
                "prediction": result["prediction"],
                "confidence": result["confidence"],
                "models": result.get("models", {}),
                "thumbnail":  True,
                "group_id":   actual_group_id,
                "heatmap": result.get("heatmap"),
            }
            new_results.append(entry)

            # Attribute the freshly-processed image to the logged-in user.
            if actor_id is not None:
                record_process(
                    actor_id, actor_email,
                    img_path.name, result["prediction"], result["confidence"],
                    datetime.now(timezone.utc).isoformat(),
                )
        else:
            # Multiple images in a group - use consensus rule
            results = classify_group_with_consensus(group_files)
            
            for i, (img_path, result) in enumerate(zip(group_files, results)):
                entry = {
                    "id":         f"OPY-{uuid.uuid4().hex[:6].upper()}",
                    "filename":   img_path.name,
                    "timestamp":  datetime.now(timezone.utc).isoformat(),
                    "prediction": result["prediction"],
                    "confidence": result["confidence"],
                    "models": result.get("models", {}),
                    "thumbnail":  True,
                    "group_id":   actual_group_id,
                    "heatmap": result.get("heatmap"),
                }
                new_results.append(entry)

                # Attribute the freshly-processed image to the logged-in user.
                if actor_id is not None:
                    record_process(
                        actor_id, actor_email,
                        img_path.name, result["prediction"], result["confidence"],
                        datetime.now(timezone.utc).isoformat(),
                    )

    # Add any previously classified images back to results (that still exist on disk)
    existing_results = [r for r in read_results() if r["filename"] in existing]
    # Combine: previously stored results + newly classified results
    all_results = existing_results + new_results
    write_results(all_results)
    
    return {
        "message": f"Classified {len(new_results)} new image(s) using model",
        "count": len(new_results),
        "mode": "model",
    }

@app.get("/results")
def get_results():
    """Return all classification results, automatically cleaning up any missing files.
    
    If the uploads folder is completely empty, results.json is also reset to []
    so every page reflects a clean state.
    """
    # If the uploads folder is empty, wipe results entirely so all pages stay in sync.
    VALID_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
    upload_files = [
        f for f in UPLOADS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in VALID_EXTS
        and not f.name.endswith("__heatmap.png")
    ] if UPLOADS_DIR.exists() else []

    if not upload_files:
        # Uploads folder is empty - clear results to ensure clean state
        write_results([])
        return {"results": []}

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


@app.get("/heatmap/{filename}")
def get_heatmap(filename: str):
    """Serve the Grad-CAM damage-localization overlay for an uploaded image.

    The overlay is generated at classify time and stored as
    `<stem>__heatmap.png` next to the original upload. If it doesn't exist
    (e.g. image was classified as Good, or model unavailable) we 404 so the
    frontend can gracefully fall back to the plain image.
    """
    safe = Path(filename).name
    stem = Path(safe).stem
    heat_path = HEATMAPS_DIR / f"{stem}__heatmap.png"
    if not heat_path.exists():
        raise HTTPException(status_code=404, detail="No damage overlay available")
    return FileResponse(str(heat_path))


@app.delete("/clear-uploads")
def clear_uploads(request: Request):
    """Delete all files in the uploads folder, the heatmaps folder, and reset the results cache."""
    deleted = 0
    if UPLOADS_DIR.exists():
        for f in UPLOADS_DIR.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                    deleted += 1
                except OSError:
                    pass

    # Also clear damage-localization overlays (they live in their own folder).
    if HEATMAPS_DIR.exists():
        for f in HEATMAPS_DIR.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass

    # Reset results cache so old user's classification results do not linger
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

    # Also remove the associated Grad-CAM damage overlay (if any) so it
    # doesn't linger after the source image is gone. Overlays live in the
    # dedicated heatmaps/ folder, not inside uploads/.
    heatmap = HEATMAPS_DIR / f"{path.stem}__heatmap.png"
    if heatmap.exists():
        try:
            heatmap.unlink()
        except OSError:
            pass

    # Also remove it from results.json if it was classified
    results = read_results()
    new_results = [r for r in results if r["filename"] != safe]
    if len(results) != len(new_results):
        write_results(new_results)

    return {"message": f"Deleted {safe}"}


def _sync_corrected_to_db():
    """
    Copy corrected images to DB folders if they're in uploads but not in DB.
    Returns (good_count, damaged_count, copied_count).
    """
    if not RAW_GOOD_DIR.exists() and not RAW_DAMAGED_DIR.exists():
        return 0, 0, 0
    
    good_files = set(RAW_GOOD_DIR.glob("*.png")) if RAW_GOOD_DIR.exists() else set()
    good_files |= set(RAW_GOOD_DIR.glob("*.jpg")) if RAW_GOOD_DIR.exists() else set()
    good_files |= set(RAW_GOOD_DIR.glob("*.jpeg")) if RAW_GOOD_DIR.exists() else set()
    good_files |= set(RAW_GOOD_DIR.glob("*.bmp")) if RAW_GOOD_DIR.exists() else set()
    
    damaged_files = set(RAW_DAMAGED_DIR.glob("*.png")) if RAW_DAMAGED_DIR.exists() else set()
    damaged_files |= set(RAW_DAMAGED_DIR.glob("*.jpg")) if RAW_DAMAGED_DIR.exists() else set()
    damaged_files |= set(RAW_DAMAGED_DIR.glob("*.jpeg")) if RAW_DAMAGED_DIR.exists() else set()
    damaged_files |= set(RAW_DAMAGED_DIR.glob("*.bmp")) if RAW_DAMAGED_DIR.exists() else set()
    
    db_files = good_files | damaged_files
    
    copied = 0
    for r in read_results():
        filename = r["filename"]
        if filename in [f.name for f in db_files]:
            continue  # Already in DB
        
        src = UPLOADS_DIR / filename
        if not src.exists():
            continue
        
        # Determine destination based on prediction
        prediction = r.get("prediction", "Good")
        dest_dir = RAW_GOOD_DIR if prediction == "Good" else RAW_DAMAGED_DIR
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        
        try:
            shutil.copy2(src, dest)
            copied += 1
            if prediction == "Good":
                good_files.add(dest)
            else:
                damaged_files.add(dest)
            print(f"[INFO] Copied {filename} to {prediction} folder")
        except Exception as e:
            print(f"[WARN] Failed to copy {filename}: {e}")
    
    # Count files in DB (all formats)
    n_good = len(good_files)
    n_damaged = len(damaged_files)
    
    return n_good, n_damaged, copied


@app.post("/train")
def train_model(user: dict = Depends(require_admin_access)):
    """
    Train/retrain the classifier using the DB images.
    
    Steps:
    1. Sync corrected images to DB folders
    2. Retrain the model with all DB images via augment_and_train.py
    3. Return success/failure notification
    """
    import traceback
    import subprocess
    import sys
    
    # Step 1: Sync any corrected images to DB
    n_good, n_damaged, copied = _sync_corrected_to_db()
    print(f"[INFO] DB status: {n_good} Good, {n_damaged} Damaged, {copied} files synced to DB")
    
    # Step 2: Retrain
    try:
        script_path = str(BASE_DIR / "augment_and_train.py")
        
        # Run the training script
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout (CNN/ViT now train more epochs with early stopping)
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            if "[ERROR] Training failed:" in result.stdout:
                err_line = [line for line in result.stdout.splitlines() if "[ERROR] Training failed:" in line]
                err_text = err_line[0].replace("[ERROR] Training failed:", "").strip() if err_line else error_msg
                raise ValueError(err_text)
            else:
                raise RuntimeError(f"Training script failed (exit code {result.returncode}):\n{error_msg}")
        
        if not STATS_PATH.exists():
            raise FileNotFoundError("Stats file not generated by training script.")
            
        stats = json.loads(STATS_PATH.read_text())
        
        # Reload models in memory cache for FastAPI
        load_models()
        
        # Step 3: Return success with detailed notification
        response = {
            "success": True,
            "message": "Model training completed successfully",
            "details": {
                "images_in_db": {
                    "good": n_good,
                    "damaged": n_damaged,
                    "total": n_good + n_damaged
                },
                "files_synced": copied,
                "model_stats": stats
            }
        }
        return response
    except ValueError as e:
        # Validation error (e.g., not enough images)
        return {
            "success": False,
            "message": f"Training failed: {str(e)}",
            "details": {
                "images_in_db": {
                    "good": n_good,
                    "damaged": n_damaged,
                    "total": n_good + n_damaged
                },
                "files_synced": copied,
                "error": "validation_error"
            }
        }
    except Exception as e:
        # Unexpected error
        error_details = traceback.format_exc()
        print(f"[ERROR] Training failed: {e}")
        print(error_details)
        return {
            "success": False,
            "message": f"Training failed with unexpected error: {str(e)}",
            "details": {
                "images_in_db": {
                    "good": n_good,
                    "damaged": n_damaged,
                    "total": n_good + n_damaged
                },
                "files_synced": copied,
                "error": "unexpected_error",
                "error_details": error_details[:1000]  # Truncate for safety
            }
        }


@app.get("/model-stats")
def model_stats():
    """Return the last training statistics."""
    if not STATS_PATH.exists():
        raise HTTPException(status_code=404, detail="No stats found. Train the model first.")
    return json.loads(STATS_PATH.read_text())


class CorrectionRequest(BaseModel):
    filename: str
    corrected_label: str

class SyncAndTrainRequest(BaseModel):
    filename: str
    corrected_label: str
    run_training: bool = True  # Whether to run the augmentation training script


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
        dest_dir = RAW_GOOD_DIR
    elif req.corrected_label == "Damaged":
        dest_dir = RAW_DAMAGED_DIR
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
    files = [f for f in UPLOADS_DIR.iterdir() if f.is_file() and f.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}] if UPLOADS_DIR.exists() else []
    
    if not files:
        write_results([])
        return {
            "total_uploaded": 0,
            "total_classified": 0
        }
        
    results = read_results()
    return {
        "total_uploaded": len(files),
        "total_classified": len(results)
    }


# ── DB Sync & Training Endpoint ──────────────────────────────────────────────────
@app.post("/sync-and-train")
def sync_and_train(req: SyncAndTrainRequest, user: dict = Depends(require_admin_access)):
    """
    Sync a corrected image to the DB folder and optionally run the augmentation training script.
    
    Steps:
    1. Copy the image from uploads to DB/Good or DB/Damaged based on corrected_label
       (If file not in uploads, create a placeholder entry - the correction still applies to results)
    2. Update the results.json with the corrected classification
    3. If run_training is True, run the augment_train.sh script
    
    Returns the training results if training was run, or just the sync status.
    """
    import subprocess
    import traceback
    
    # Step 1: Try to find the file in uploads
    src_file = UPLOADS_DIR / req.filename
    file_found_in_uploads = src_file.exists()
    
    # Step 2: Determine destination directory
    if req.corrected_label == "Good":
        dest_dir = RAW_GOOD_DIR
    elif req.corrected_label == "Damaged":
        dest_dir = RAW_DAMAGED_DIR
    else:
        raise HTTPException(status_code=400, detail="Invalid corrected label. Must be 'Good' or 'Damaged'.")
    
    # Step 3: Ensure destination directory exists and copy file if found
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / req.filename
    
    if file_found_in_uploads:
        try:
            shutil.copy2(src_file, dest_file)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to copy file to DB: {str(e)}")
    else:
        # File not in uploads - we still allow the correction to be recorded in results
        # This handles the case where uploads were cleared but user wants to correct past results
        print(f"[INFO] File {req.filename} not found in uploads, but correction will be recorded in results")
    
    # Step 4: Update results.json
    results = read_results()
    updated = False
    for r in results:
        if r["filename"] == req.filename:
            r["prediction"] = req.corrected_label
            r["confidence"] = 1.0
            r["corrected"] = True
            updated = True
            break
    
    if not updated:
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
    
    # Step 5: Run training script if requested
    training_result = None
    if req.run_training:
        try:
            # Get the project root directory
            import sys
            script_path = str(BASE_DIR / "augment_and_train.py")
            
            # Run the training script
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout (CNN/ViT now train more epochs with early stopping)
            )
            
            # Reload models in memory cache for FastAPI on success
            if result.returncode == 0:
                load_models()
                
            training_result = {
                "success": result.returncode == 0,
                "stdout": result.stdout[-5000:] if len(result.stdout) > 5000 else result.stdout,  # Truncate for response
                "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            training_result = {
                "success": False,
                "error": "Training script timed out after 10 minutes"
            }
        except Exception as e:
            training_result = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()[-1000:]
            }
    
    response = {
        "message": f"Successfully synced {req.filename} to {req.corrected_label} folder" + ("" if file_found_in_uploads else " (file not in uploads, correction recorded in results)"),
        "filename": req.filename,
        "destination": str(dest_file),
        "training": training_result
    }
    
    return response

@app.post("/classify-stream")
async def classify_stream(request: Request):
    VALID = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}
    files = [
        f for f in UPLOADS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in VALID
        and not f.name.endswith("__heatmap.png")
    ]

    if not files:
        raise HTTPException(status_code=400, detail="No uploaded images to classify.")

    use_model = load_models()
    if not use_model:
        raise HTTPException(
            status_code=400,
            detail="Ensemble models are not trained yet. Please go to the Admin page and click 'Retrain Model' first."
        )

    actor = current_user(request)
    actor_id = actor["id"] if actor else None
    actor_email = actor["email"] if actor else None

    existing = {r["filename"]: r for r in read_results()}

    groups = {}
    for img_path in files:
        if img_path.name in existing:
            continue
        group_id = parse_group_id(img_path.name)
        if group_id is None:
            group_id = img_path.name
        if group_id not in groups:
            groups[group_id] = []
        groups[group_id].append(img_path)

    async def event_generator():
        new_results = []
        total_groups = len(groups)
        processed_groups = 0

        for group_id, group_files in groups.items():
            # Yield progress BEFORE processing
            yield json.dumps({
                "type": "progress",
                "progress": processed_groups,
                "total": total_groups,
                "current": group_files[0].name if len(group_files) == 1 else f"Group: {group_id}"
            }) + "\n"
            await asyncio.sleep(0)

            actual_group_id = None if len(group_files) == 1 and "___" not in group_files[0].name else group_id
            
            if len(group_files) == 1:
                img_path = group_files[0]
                result = await asyncio.to_thread(classify_image, img_path)
                
                entry = {
                    "id":         f"OPY-{uuid.uuid4().hex[:6].upper()}",
                    "filename":   img_path.name,
                    "timestamp":  datetime.now(timezone.utc).isoformat(),
                    "prediction": result["prediction"],
                    "confidence": result["confidence"],
                    "models": result.get("models", {}),
                    "thumbnail":  True,
                    "group_id":   actual_group_id,
                    "heatmap": result.get("heatmap"),
                }
                new_results.append(entry)

                if actor_id is not None:
                    await asyncio.to_thread(record_process, actor_id, actor_email, img_path.name, result["prediction"], result["confidence"], datetime.now(timezone.utc).isoformat())
            else:
                results = await asyncio.to_thread(classify_group_with_consensus, group_files)
                for i, (img_path, result) in enumerate(zip(group_files, results)):
                    entry = {
                        "id":         f"OPY-{uuid.uuid4().hex[:6].upper()}",
                        "filename":   img_path.name,
                        "timestamp":  datetime.now(timezone.utc).isoformat(),
                        "prediction": result["prediction"],
                        "confidence": result["confidence"],
                        "models": result.get("models", {}),
                        "thumbnail":  True,
                        "group_id":   actual_group_id,
                        "heatmap": result.get("heatmap"),
                    }
                    new_results.append(entry)
                    if actor_id is not None:
                        await asyncio.to_thread(record_process, actor_id, actor_email, img_path.name, result["prediction"], result["confidence"], datetime.now(timezone.utc).isoformat())
            
            processed_groups += 1
            # Yield progress AFTER processing
            yield json.dumps({
                "type": "progress",
                "progress": processed_groups,
                "total": total_groups,
                "current": "Done"
            }) + "\n"
            await asyncio.sleep(0)

        existing_results = [r for r in read_results() if r["filename"] in existing]
        all_results = existing_results + new_results
        await asyncio.to_thread(write_results, all_results)
        
        yield json.dumps({
            "type": "result",
            "message": f"Classified {len(new_results)} new image(s) using model",
            "count": len(new_results),
            "mode": "model"
        }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@app.post("/train-stream")
async def train_stream(user: dict = Depends(require_admin_access)):
    import sys
    import subprocess
    import asyncio
    
    # Sync corrected images before we start the subprocess stream
    n_good, n_damaged, copied = _sync_corrected_to_db()
    
    async def event_generator():
        # Let frontend know we synced files
        yield json.dumps({
            "type": "log",
            "message": f"[INFO] DB status: {n_good} Good, {n_damaged} Damaged, {copied} files synced to DB"
        }) + "\n"
        await asyncio.sleep(0)
        
        script_path = str(BASE_DIR / "augment_and_train.py")
        
        # Use standard Popen and to_thread to avoid NotImplementedError on Windows SelectorEventLoop
        # Pass -u to Python so stdout is unbuffered and streams live to the frontend
        process = subprocess.Popen(
            [sys.executable, "-u", script_path],
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        while True:
            line = await asyncio.to_thread(process.stdout.readline)
            if not line:
                break
            text = line.rstrip()
            yield json.dumps({
                "type": "log",
                "message": text
            }) + "\n"
            
        await asyncio.to_thread(process.wait)
        
        if process.returncode == 0:
            # reload models
            await asyncio.to_thread(load_models)
            stats = {}
            if STATS_PATH.exists():
                stats = json.loads(STATS_PATH.read_text())
                
            yield json.dumps({
                "type": "result",
                "success": True,
                "message": "Model training completed successfully",
                "stats": stats
            }) + "\n"
        else:
            yield json.dumps({
                "type": "result",
                "success": False,
                "message": f"Training failed with exit code {process.returncode}"
            }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
