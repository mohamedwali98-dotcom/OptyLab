# OptyLab - Visual Quality Dashboard

OptyLab is a high-precision computer vision pipeline and full-stack dashboard designed to detect defects and verify the quality of manufactured eye lenses.

## Architecture

OptyLab uses a **3-Model Voting Ensemble** to maximize accuracy and precision on fine details.

### 1. The Ensemble Models
- **SVM (Support Vector Machine):** Extracts Histogram of Oriented Gradients (HOG) features from the images to detect edge and texture anomalies.
- **CNN (ResNet18):** A deep Convolutional Neural Network pretrained on ImageNet, fine-tuned to extract hierarchical spatial features.
- **ViT (Vision Transformer):** A state-of-the-art transformer architecture (`torchvision.models.vit_b_16`) that models global image context using self-attention mechanisms.

### 2. High Precision Processing
Because eye lenses require extreme precision, all models are fed high-resolution images (`256x256`) using **Bicubic Interpolation**. This preserves fine edges and details that standard bilinear resizing would blur.

### 3. Majority Voting
During inference, the image is passed through all three models independently. A final prediction is made using a majority vote (e.g., if CNN and ViT say "Good" but SVM says "Damaged", the system outputs "Good").

## Project Structure

```
OptyLab/
├── DB/                          # Image database (at project root)
│   ├── RawImagesDamaged/        # Original damaged images for augmentation
│   ├── RawImagesGood/           # Original good images for augmentation
│   ├── Damaged/                 # Augmented damaged images
│   └── Good/                    # Augmented good images
├── visual_quality_dashboard/    # Dashboard application
│   ├── docker/                  # ← Docker shortcuts and multi-container images
│   │   ├── Dockerfile.augment_train # Training pipeline image
│   │   ├── Dockerfile.run_all       # Full stack orchestration image
│   │   ├── augment_train.sh         # Shortcut for training
│   │   ├── run_all.sh               # Shortcut for full stack
│   │   └── README.md                # Docker documentation
│   ├── backend/
│   │   ├── classifier.py         # Orchestrator for the ensemble model
│   │   ├── classifier_utils.py   # Shared config, data loaders, and transforms
│   │   ├── classifier_svm.py     # SVM/HOG implementation
│   │   ├── classifier_cnn.py     # ResNet18 implementation
│   │   ├── classifier_vit.py     # Vision Transformer implementation
│   │   ├── main.py               # FastAPI backend server
│   │   ├── requirements.txt      # Python dependencies
│   │   ├── augment_and_train.py  # Data augmentation + training pipeline
│   │   ├── Dockerfile            # Container for the ML backend
│   │   └── model/                # Trained model weights
│   ├── src/                      # Vite + React Frontend
│   ├── docker-compose.yml        # Orchestrates Frontend + Backend
│   ├── run_all.py                # Local orchestration script
│   └── README.md                 # Dashboard documentation
├── .gitignore
└── package-lock.json
```

## Running the Application

### Using Docker Compose (Recommended)

Start the entire application stack:

```bash
# From the project root
cd /c/Users/moham/Desktop/OptyLab
docker compose -f visual_quality_dashboard/docker-compose.yml up --build
```

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000`

### Using Docker Shortcuts

**Run training pipeline:**
```bash
cd /c/Users/moham/Desktop/OptyLab
./visual_quality_dashboard/docker/augment_train.sh
```

**Run full stack (combined image):**
```bash
cd /c/Users/moham/Desktop/OptyLab
./visual_quality_dashboard/docker/run_all.sh
```

**Run in detached mode:**
```bash
./visual_quality_dashboard/docker/run_all.sh -d
```

### Running Locally

Run the application directly on your machine:

```bash
cd visual_quality_dashboard
python run_all.py
```

*(Make sure you have Node.js and Python installed)*

## Training with Docker

Run the augment_and_train pipeline to augment data and retrain models:

```bash
# Run with default augmentation count (10)
cd /c/Users/moham/Desktop/OptyLab
./visual_quality_dashboard/docker/augment_train.sh

# Run with custom augmentation count (15 copies per image)
cd /c/Users/moham/Desktop/OptyLab
AUG_PER_IMAGE=15 ./visual_quality_dashboard/docker/augment_train.sh
```

## API Endpoints

- `GET /results` - Fetch historical analysis results.
- `POST /classify` - Upload an image and get a classification from the ensemble.
- `POST /train` - Retrain the ensemble model on the `DB/` directory.
- `POST /correct-prediction` - Override a prediction and move the image to the correct folder.
- `POST /upload` - Upload images for classification.
- `GET /queue` - List images waiting for classification.
- `DELETE /clear-uploads` - Clear all uploaded images and results.

## Docker Commands

```bash
# Build images
cd /c/Users/moham/Desktop/OptyLab
docker build -t optylab/augment_train -f visual_quality_dashboard/docker/Dockerfile.augment_train .
docker build -t optylab/run_all -f visual_quality_dashboard/docker/Dockerfile.run_all .

# Start services
./visual_quality_dashboard/docker/run_all.sh -d    # Full stack via run_all
docker compose -f visual_quality_dashboard/docker-compose.yml up  # Full stack via compose

# View logs
docker logs -f optylab_backend
docker logs -f optylab_run_all

# Stop services
docker compose -f visual_quality_dashboard/docker-compose.yml down
```

## Data Volumes

Docker volumes for persisting data:

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `OptyLab/DB/` | `/app/DB` | Image database (Good/Damaged/RawImagesGood/RawImagesDamaged) |
| `visual_quality_dashboard/backend/model/` | `/app/model` | Trained model weights (.pth, .pkl files, stats.json) |

## Development

```bash
# Rebuild images
docker build --no-cache -t optylab/augment_train -f visual_quality_dashboard/docker/Dockerfile.augment_train .
docker build --no-cache -t optylab/run_all -f visual_quality_dashboard/docker/Dockerfile.run_all .

# Clean up
docker image prune -f
docker container prune -f
```