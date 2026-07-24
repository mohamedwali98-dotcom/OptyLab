"""
main.py
=======
FastAPI backend for the OptyLab Visual Quality Inspector.

Start with:
    uvicorn main:app --reload --port 8000
"""

import json
import uuid
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from classifier import train_and_evaluate, load_model, classify_image, STATS_PATH, MODEL_PATH

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

# ── Helpers ──────────────────────────────────────────────────────────────────
def read_results() -> list:
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return []

def write_results(data: list):
    RESULTS_FILE.write_text(json.dumps(data, indent=2))


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "OptyLab API running"}


@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Accept PNG images from the frontend and save them to the upload queue."""
    saved = []
    for f in files:
        if not f.content_type.startswith("image/"):
            continue
        safe_name = Path(f.filename).name
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


def _mock_classify() -> dict:
    """Random Good/Damaged label — used when the real model is not trained yet."""
    prediction = random.choice(["Good", "Damaged"])
    confidence = round(random.uniform(0.55, 0.99), 4)
    return {"prediction": prediction, "confidence": confidence}


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

    use_model = MODEL_PATH.exists()
    model = load_model() if use_model else None
    if use_model and model is None:
        use_model = False   # model file corrupt — fall back to mock

    existing = {r["filename"]: r for r in read_results()}

    new_results = []
    for img_path in sorted(files):
        if img_path.name in existing:
            new_results.append(existing[img_path.name])
            continue
        result = classify_image(img_path, model) if use_model else _mock_classify()
        entry = {
            "id":         f"OPY-{uuid.uuid4().hex[:6].upper()}",
            "filename":   img_path.name,
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "prediction": result["prediction"],
            "confidence": result["confidence"],
            "thumbnail":  True,
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
    """Return all classification results."""
    return {"results": read_results()}


@app.get("/thumbnail/{filename}")
def get_thumbnail(filename: str):
    """Serve uploaded image as thumbnail."""
    safe = Path(filename).name
    path = UPLOADS_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(path))


@app.delete("/clear-uploads")
def clear_uploads():
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
def train_model():
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
