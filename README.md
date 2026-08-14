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
│   ├── run_all.py               # Starts the Docker Compose stack
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

## Quick Start (Docker)

The app runs as **2 containers** built from `docker-compose.yml`:

| Service | Port | Image |
|---------|------|-------|
| Backend (FastAPI + ML) | `http://localhost:8000` | `visual_quality_dashboard-backend` |
| Frontend (React → Nginx) | `http://localhost:8080` | `visual_quality_dashboard-frontend` |

### Option A — Using `run_all.py` (recommended)

```bash
# From the project root
cd OptyLab
python visual_quality_dashboard/run_all.py
```

This builds both Docker images and starts the containers.

### Option B — Using docker-compose directly

```bash
# From the project root
cd OptyLab

# Build and start both containers (foreground)
docker compose -f visual_quality_dashboard/docker-compose.yml up --build

# Or detached (background)
docker compose -f visual_quality_dashboard/docker-compose.yml up --build -d

# Stop all containers
docker compose -f visual_quality_dashboard/docker-compose.yml down
```

---

## Running Locally (Development, no Docker)

Requires **Python 3.14** (backed by `C:/Python314/python.exe`) and **Node.js**.

### 1. Install backend dependencies

```bash
cd visual_quality_dashboard/backend
C:/Python314/python.exe -m pip install -r requirements.txt
```

### 2. Start the backend

```bash
C:/Python314/python.exe -m uvicorn main:app --reload --port 8000
```

### 3. Start the frontend (separate terminal)

```bash
cd visual_quality_dashboard
npm install
npm run dev
```

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

---

## Augment Data & Train Models

### Option A — Via `augment_and_train.py` (Python)

```bash
# From the project root
C:/Python314/python.exe visual_quality_dashboard/backend/augment_and_train.py

# Custom number of augmented copies per image (default: 10)
AUG_PER_IMAGE=15 C:/Python314/python.exe visual_quality_dashboard/backend/augment_and_train.py
```

### Option B — Via Docker

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