# Docker Shortcuts

This directory contains Docker setup files and shortcuts for running OptyLab components.

## Directory Structure

```
docker/
├── Dockerfile.augment_train  # Build for training pipeline
├── Dockerfile.run_all        # Build for full stack
├── augment_train.sh          # Shortcut script for training
├── run_all.sh                # Shortcut script for full stack
├── nginx.conf                # Nginx configuration for combined image
└── README.md                 # This file

See the main project README.md at the OptyLab root for complete documentation.
```

## Prerequisites

- Docker installed (Docker Desktop on Windows)
- Git Bash or WSL2 for running shell scripts (on Windows)

## Available Docker Images

### 1. Frontend Only (Recommended for Production)
**Port:** 8080 (HTTP)

Uses the existing `Dockerfile` and `docker-compose.yml` configuration from the project root.

```bash
# From the project root (OptyLab directory)
cd /c/Users/moham/Desktop/OptyLab

# Start the full stack using docker-compose
docker compose -f visual_quality_dashboard/docker-compose.yml up --build
```

### 2. augment_and_train (Training Pipeline)
**Purpose:** Run the complete data augmentation + model training pipeline.

**Usage:**

```bash
# Option 1: Using the shortcut script (recommended)
# Run from the project root directory
cd /c/Users/moham/Desktop/OptyLab
./visual_quality_dashboard/docker/augment_train.sh

# Option 2: Manual build and run
docker build -t optylab/augment_train -f visual_quality_dashboard/docker/Dockerfile.augment_train .
docker run --rm \
  -e AUG_PER_IMAGE=10 \
  -v /c/Users/moham/Desktop/OptyLab/DB:/app/DB \
  -v /c/Users/moham/Desktop/OptyLab/visual_quality_dashboard/backend/model:/app/model \
  optylab/augment_train

# On Windows Git Bash, use:
# cd /c/Users/moham/Desktop/OptyLab
# ./visual_quality_dashboard/docker/augment_train.sh
```

**Environment Variables:**
- `AUG_PER_IMAGE`: Number of augmented copies per source image (default: 10)

**Volumes Mounted:**
- DB data: `OptyLab/DB` → `/app/DB` (image data)
- Model: `visual_quality_dashboard/backend/model` → `/app/model` (trained models)

### 3. run_all (Full Stack Orchestration)
**Purpose:** Run both frontend and backend together in a single container.

**Usage:**

```bash
# Option 1: Using the shortcut script (recommended)
# Run from the project root directory
cd /c/Users/moham/Desktop/OptyLab
./visual_quality_dashboard/docker/run_all.sh

# Run in detached mode
./visual_quality_dashboard/docker/run_all.sh -d

# Build only (don't run)
./visual_quality_dashboard/docker/run_all.sh -b

# Option 2: Manual
docker build -t optylab/run_all -f visual_quality_dashboard/docker/Dockerfile.run_all .
docker run -d --name optylab_run_all \
  -p 8080:80 \
  -p 8000:8000 \
  -v /c/Users/moham/Desktop/OptyLab/DB:/app/DB \
  -v /c/Users/moham/Desktop/OptyLab/visual_quality_dashboard/backend/model:/app/model \
  optylab/run_all
```

**Ports:**
- `8080` (HTTP) - Frontend
- `8000` (HTTP) - Backend API

## Quick Reference Table

| Image | Tag | Ports | Volumes |
|-------|-----|-------|---------|
| frontend (compose) | optylab/frontend:latest | 8080 | DB/, models/ |
| augment_train | optylab/augment_train:latest | - | DB/, model/ |
| run_all | optylab/run_all:latest | 8080, 8000 | DB/, model/ |

## Data Volumes

The Docker images mount the following host directories:

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `OptyLab/DB/` | `/app/DB` | Image database (Good/Damaged/RawImagesGood/RawImagesDamaged) |
| `visual_quality_dashboard/backend/model/` | `/app/model` | Trained model weights (.pth, .pkl files, stats.json) |

## Common Commands

```bash
# Build all images
cd /c/Users/moham/Desktop/OptyLab
docker build -t optylab/augment_train -f visual_quality_dashboard/docker/Dockerfile.augment_train .
docker build -t optylab/run_all -f visual_quality_dashboard/docker/Dockerfile.run_all .

# Start services
docker compose up           # Full stack via docker-compose
./visual_quality_dashboard/docker/run_all.sh    # Full stack via run_all image
./visual_quality_dashboard/docker/augment_train.sh  # Training pipeline

# View logs
docker logs -f optylab_backend
docker logs -f optylab_run_all

# Stop services
docker compose down
docker stop optylab_run_all

# Clean up
docker image prune -f
docker container prune -f
```

## Development

### Building images

```bash
# Rebuild specific images with no cache
docker build --no-cache -t optylab/augment_train -f docker/Dockerfile.augment_train .
docker build --no-cache -t optylab/run_all -f docker/Dockerfile.run_all .

# Build frontend only (via docker-compose)
docker compose build frontend
```

### Running Training

```bash
# Run training with default augmentation count (10)
./visual_quality_dashboard/docker/augment_train.sh

# Run training with 15 augmented copies per image
AUG_PER_IMAGE=15 ./visual_quality_dashboard/docker/augment_train.sh
```

### Full Stack Development

```bash
# Start in detached mode
./visual_quality_dashboard/docker/run_all.sh -d

# Stop and remove container
docker stop optylab_run_all
docker rm optylab_run_all
```