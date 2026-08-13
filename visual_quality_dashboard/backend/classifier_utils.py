import os
import json
import numpy as np
from pathlib import Path
from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent
DB_DIR      = BASE_DIR.parent.parent / "DB"
GOOD_DIR    = DB_DIR / "Good"
DAMAGED_DIR = DB_DIR / "Damaged"
RAW_GOOD_DIR = DB_DIR / "RawImagesGood"
RAW_DAMAGED_DIR = DB_DIR / "RawImagesDamaged"
MODEL_DIR   = BASE_DIR / "model"
STATS_PATH  = MODEL_DIR / "stats.json"
# Damage-localization overlays live in their own folder, a sibling of `uploads/`.
# Keeping them out of `uploads/` stops them from showing up in the transfer queue.
HEATMAPS_DIR = BASE_DIR / "heatmaps"

DEVICE      = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def load_image_paths():
    VALID = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}
    paths = []
    labels = []
    for folder, label, name in [(GOOD_DIR, 0, "Good"), (DAMAGED_DIR, 1, "Damaged")]:
        if not folder.exists():
            continue
        files = [f for f in folder.iterdir() if f.suffix.lower() in VALID]
        for f in files:
            # Skip corrupt/undecodable files so they can't crash training later
            try:
                with Image.open(f) as im:
                    im.verify()
            except Exception:
                print(f"[WARN] Skipping unreadable image: {f.name}")
                continue
            paths.append(f)
            labels.append(label)
    return paths, labels


# ── PyTorch Dataset & Transforms ─────────────────────────────────────────────
class ImageDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        self.paths = paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        path = self.paths[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx]

# High precision resizing for eye lenses (224x224, BICUBIC)
pytorch_transform = transforms.Compose([
    transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def train_pytorch_model(model, train_loader, epochs=3):
    import torch.nn as nn
    import torch.optim as optim
    
    model.to(DEVICE)
    model.train()
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    for epoch in range(epochs):
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            outputs = model(inputs)
            if hasattr(outputs, "logits"):
                outputs = outputs.logits
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

def evaluate_pytorch_model(model, loader):
    model.to(DEVICE)
    model.eval()
    all_preds = []
    all_labels = []
    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(DEVICE)
            outputs = model(inputs)
            if hasattr(outputs, "logits"):
                outputs = outputs.logits
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels.extend(labels.numpy())
    return np.array(all_labels), np.array(all_preds)
