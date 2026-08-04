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
visual_quality_dashboard/
├── backend/
│   ├── classifier.py         # Orchestrator for the ensemble model
│   ├── classifier_utils.py   # Shared config, data loaders, and transforms
│   ├── classifier_svm.py     # SVM/HOG implementation
│   ├── classifier_cnn.py     # ResNet18 implementation
│   ├── classifier_vit.py     # Vision Transformer implementation
│   ├── main.py               # FastAPI backend server
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Container for the ML backend
├── src/                      # Vite + React Frontend
├── docker-compose.yml        # Orchestrates Frontend + Backend
└── DB/                       # Database of images (Good/Damaged)
```

## Running the Application

### Using Docker (Recommended)
You can spin up the entire application stack using Docker Compose. This ensures the ML environment matches exactly.
```bash
docker compose up --build
```
- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000`

### Running Locally
You can run the application directly on your machine using the helper script:
```bash
python run_all.py
```
*(Make sure you have Node.js and Python installed)*

## API Endpoints

- `GET /results`: Fetch historical analysis results.
- `POST /classify`: Upload an image and get a classification from the ensemble.
- `POST /train`: Retrain the ensemble model on the `DB/` directory.
- `POST /correct-prediction`: Override a prediction and move the image to the correct folder in `DB/`.
