# OptyLab - Visual Quality Dashboard

OptyLab is a high-precision computer vision pipeline and full-stack dashboard designed to detect defects and verify the quality of manufactured eye lenses using a **3-Model Voting Ensemble** (SVM + CNN ResNet18 + ViT).

## Project Structure

```
OptyLab/
├── DB/                          # Image database (at project root)
│   ├── RawImagesDamaged/        # Original damaged images for augmentation
│   ├── RawImagesGood/           # Original good images for augmentation
│   ├── Damaged/                 # Augmented damaged images
│   └── Good/                    # Augmented good images
├── visual_quality_dashboard/    # Dashboard application
│   ├── docker-compose.yml       # Orchestrates Frontend + Backend (2 containers)
│   ├── run_all.py               # Launcher: local by default, --docker to containerize
│   ├── Dockerfile               # Frontend image (Vite → Nginx)
│   ├── backend/
│   │   ├── main.py              # FastAPI backend server
│   │   ├── Dockerfile           # Backend image (FastAPI + ML)
│   │   ├── requirements.txt     # Python dependencies
│   │   ├── augment_and_train.py # Augment data + train models
│   │   ├── classifier*.py       # SVM / CNN / ViT ensemble
│   │   └── ...
│   └── src/                     # Vite + React Frontend
└── README.md                    # This file
```

---

## Quick Start (Local — recommended)

One command starts both the backend and frontend as local processes — **no
Docker required, nothing gets built**:

```bash
# From the project root
cd OptyLab
python visual_quality_dashboard/run_all.py
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

The first run installs frontend packages automatically (`npm install`) if
`node_modules/` isn't present yet. Backend Python dependencies are **not**
auto-installed (they're heavy — torch, torchvision) — if `uvicorn` isn't
importable yet, the script tells you the exact command to run:

```bash
python -m pip install -r visual_quality_dashboard/backend/requirements.txt
```

Requires Python 3.10+ (the codebase uses `X | None` type syntax) and Node.js.
Press `Ctrl+C` to stop both processes.

### Flags

| Command | What it does |
|---|---|
| `python visual_quality_dashboard/run_all.py` | Local backend + frontend (default) |
| `python visual_quality_dashboard/run_all.py --train` | Runs `augment_and_train.py` first, then serves locally |
| `python visual_quality_dashboard/run_all.py --docker` | Serves via `docker compose up` instead (builds only if images are missing) |
| `python visual_quality_dashboard/run_all.py --docker --build` | Docker, forcing an image rebuild |

### Running backend/frontend manually (equivalent to the local default)

```bash
# Terminal 1 — backend
cd visual_quality_dashboard/backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd visual_quality_dashboard
npm install
npm run dev
```

---

## Docker (optional)

The app can also run as **2 containers** via `docker-compose.yml`. Use this
if you don't want Python/Node installed locally, or want an isolated
environment.

| Service | Port | Image |
|---------|------|-------|
| Backend (FastAPI + ML) | `http://localhost:8000` | `visual_quality_dashboard-backend` |
| Frontend (React → Nginx) | `http://localhost:8080` | `visual_quality_dashboard-frontend` |

### Option A — `run_all.py --docker`

```bash
# From the project root
cd OptyLab
python visual_quality_dashboard/run_all.py --docker         # build only if images are missing
python visual_quality_dashboard/run_all.py --docker --build # force a rebuild
```

### Option B — docker compose directly

```bash
# From the project root
cd OptyLab

# Start (builds only if images are missing)
docker compose -f visual_quality_dashboard/docker-compose.yml up

# Force a rebuild
docker compose -f visual_quality_dashboard/docker-compose.yml up --build

# Detached (background)
docker compose -f visual_quality_dashboard/docker-compose.yml up -d

# Stop all containers
docker compose -f visual_quality_dashboard/docker-compose.yml down
```

**Note:** neither `run_all.py` nor plain `docker compose up` rebuilds images
on every launch — Compose only builds a service the first time its image is
missing, or when `--build` is passed. Docker's own layer cache still applies,
so even an explicit `--build` after a small code change is fast.

---

## Augment Data & Train Models

Training now holds out a **grouped test split** (by raw source image, so
augmented copies of one photo never leak across the split) and reports honest
held-out accuracy/precision/recall/F1 + a confusion matrix in
`backend/model/stats.json`, instead of scoring each model on its own training
data.

### Option A — Via `run_all.py --train` (runs then serves)

```bash
# From the project root
python visual_quality_dashboard/run_all.py --train
```

### Option B — Via `augment_and_train.py` directly (Python)

```bash
# From the project root
python visual_quality_dashboard/backend/augment_and_train.py

# Custom number of augmented copies per image (default: 10)
AUG_PER_IMAGE=15 python visual_quality_dashboard/backend/augment_and_train.py
```

### Option C — Via Docker

```bash
# From the project root
cd OptyLab

# Build the training image (once)
docker build -t optylab/augment_train -f visual_quality_dashboard/docker/Dockerfile.augment_train .

# Run the augment + train pipeline
docker run --rm \
  -e AUG_PER_IMAGE=10 \
  -v "$(pwd)/DB:/app/DB" \
  -v "$(pwd)/visual_quality_dashboard/backend/model:/app/model" \
  optylab/augment_train
```

**Note:** This Docker image is separate from the 2 application containers — it is only used for the training pipeline.

---

## API Endpoints

- `GET /results` - Fetch historical analysis results.
- `POST /classify` - Upload an image and get a classification from the ensemble.
- `POST /train` - Retrain the ensemble model on the `DB/` directory (admin only).
- `POST /correct-prediction` - Override a prediction and move the image to the correct folder.
- `POST /upload` - Upload images for classification.
- `GET /queue` - List images waiting for classification.
- `DELETE /clear-uploads` - Clear all uploaded images and results.
- `POST /auth/register` - Register a new user account.
- `POST /auth/login` - Login with email and password.

---

## Data Volumes

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `OptyLab/DB/` | `/app/DB` | Image database (Good/Damaged/RawImagesGood/RawImagesDamaged) |
| `visual_quality_dashboard/backend/model/` | `/app/model` | Trained model weights (.pth, .pkl, stats.json) |

These are mounted as volumes — they are **not** inside the Docker images. Copy them along with your project when moving to another machine.
