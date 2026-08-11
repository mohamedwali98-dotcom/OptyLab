# ── Base Image ──
FROM python:3.11-slim

# ── System Dependencies ──
# Required for OpenCV/skimage (libgl1-mesa-glx) and HOG feature extraction
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Working Directory ──
WORKDIR /app

# ── Copy requirements first (for caching) ──
COPY requirements.txt .

# ── Install Python Dependencies ──
RUN pip install --no-cache-dir -r requirements.txt

# ── Application Code ──
COPY . .

# ── Port & Execution ──
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]