import os
import re
import copy
import json
import random
import numpy as np
from pathlib import Path
from PIL import Image
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset
from torchvision import transforms

# ── Paths ────────────────────────────────────────────────────────────────────
# DB_DIR / MODEL_DIR are overridable via env vars so a Docker container (or any
# machine where the data doesn't live two directories up from this file) can
# point them at the correct mounted volume, e.g.:
#   OPTYLAB_DB_DIR=/app/DB  OPTYLAB_MODEL_DIR=/app/model
BASE_DIR    = Path(__file__).resolve().parent
DB_DIR      = Path(os.environ.get("OPTYLAB_DB_DIR") or (BASE_DIR.parent.parent / "DB"))
GOOD_DIR    = DB_DIR / "Good"
DAMAGED_DIR = DB_DIR / "Damaged"
RAW_GOOD_DIR = DB_DIR / "RawImagesGood"
RAW_DAMAGED_DIR = DB_DIR / "RawImagesDamaged"
MODEL_DIR   = Path(os.environ.get("OPTYLAB_MODEL_DIR") or (BASE_DIR / "model"))
MODEL_DIR.mkdir(parents=True, exist_ok=True)
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


# ── Grouping (for leakage-free splits) ───────────────────────────────────────
# The dataset on disk is a handful of raw photos plus ~10 augmented copies of
# each (named "{rawstem}_aug{N}.jpg"). A naive random split would put near-
# duplicate copies of the same physical lens on both sides of train/test,
# making the held-out accuracy meaningless. group_id_for() collapses an
# augmented filename back to its raw source so a grouped split
# (GroupShuffleSplit / GroupKFold) keeps every copy of one source image on the
# same side of the split. Labels are folded into the id so a Good and a
# Damaged image can never collide into the same group.
def group_id_for(path: Path, label: int) -> str:
    base = re.sub(r"_aug\d+$", "", path.stem)
    return f"{label}:{base}"

def load_image_paths_with_groups():
    """Same as load_image_paths(), plus a group id per image so callers can do
    a grouped train/test split that never separates augmented siblings."""
    paths, labels = load_image_paths()
    groups = [group_id_for(p, l) for p, l in zip(paths, labels)]
    return paths, labels, groups


def class_weights_for(labels) -> list:
    """Inverse-frequency class weights for CrossEntropyLoss, so the minority
    class in a train split isn't drowned out."""
    counts = np.bincount(labels, minlength=2).astype(float)
    counts[counts == 0] = 1.0
    weights = counts.sum() / (2.0 * counts)
    return weights.tolist()


# ── PyTorch Dataset & Transforms ─────────────────────────────────────────────
class ImageDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        self.paths = paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        # A file can be transiently unreadable mid-training (antivirus scan,
        # search indexer, concurrent access from another process) even though
        # load_image_paths() confirmed it opened fine at listing time. Retry a
        # few other indices rather than crashing a multi-minute training run
        # on a single flaky read.
        last_error = None
        for attempt in range(5):
            use_idx = idx if attempt == 0 else random.randrange(len(self.paths))
            path = self.paths[use_idx]
            try:
                img = Image.open(path).convert("RGB")
            except (OSError, FileNotFoundError) as e:
                print(f"[WARN] Skipping unreadable image during training: {path.name} ({e})")
                last_error = e
                continue
            if self.transform:
                img = self.transform(img)
            return img, self.labels[use_idx]
        raise RuntimeError(f"ImageDataset: too many consecutive unreadable images ({last_error})")

# High precision resizing for eye lenses (224x224, BICUBIC).
# Deterministic — used for validation, test, and all inference (also imported
# directly by gradcam.py), so it must stay stable across changes here.
pytorch_transform = transforms.Compose([
    transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

# Stochastic training-only transform. On top of the offline-augmented copies
# already on disk, this adds a fresh random crop/flip/rotation/color jitter on
# every epoch so the CNN/ViT don't just memorize the fixed augmented set.
train_transform = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.8, 1.0), interpolation=transforms.InterpolationMode.BICUBIC),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(10),
    transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])


def train_pytorch_model(model, train_loader, val_loader=None, epochs=3,
                         head_params=None, lr_head=1e-3, lr_backbone=1e-4,
                         class_weights=None, patience=3):
    """
    Fine-tune a torchvision classification model with discriminative learning
    rates: a low rate for the pretrained backbone and a higher rate for the
    freshly-initialized classification head, on a cosine LR schedule.

    If val_loader is given, the model is evaluated on it after every epoch and
    the best-val-loss weights are kept (early stopping after `patience` epochs
    without improvement) instead of unconditionally keeping the last epoch.
    Without a val_loader, it just trains for the fixed number of epochs.

    Returns the model (weights loaded in-place with the best checkpoint found).
    """
    model.to(DEVICE)

    head_params = list(head_params) if head_params else []
    head_ids = {id(p) for p in head_params}
    backbone_params = [p for p in model.parameters() if id(p) not in head_ids]

    param_groups = []
    if backbone_params:
        param_groups.append({"params": backbone_params, "lr": lr_backbone})
    if head_params:
        param_groups.append({"params": head_params, "lr": lr_head})
    if not param_groups:
        param_groups = [{"params": model.parameters(), "lr": lr_head}]

    optimizer = optim.Adam(param_groups)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(epochs, 1))

    weight_tensor = None
    if class_weights is not None:
        weight_tensor = torch.tensor(class_weights, dtype=torch.float32, device=DEVICE)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)

    best_state = None
    best_val_loss = float("inf")
    stale_epochs = 0

    for epoch in range(epochs):
        model.train()
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            outputs = model(inputs)
            if hasattr(outputs, "logits"):
                outputs = outputs.logits
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
        scheduler.step()

        if val_loader is not None and len(val_loader.dataset) > 0:
            val_loss = _eval_loss(model, val_loader, criterion)
            print(f"    epoch {epoch + 1}/{epochs}  val_loss={val_loss:.4f}")
            if val_loss < best_val_loss - 1e-4:
                best_val_loss = val_loss
                best_state = copy.deepcopy(model.state_dict())
                stale_epochs = 0
            else:
                stale_epochs += 1
                if stale_epochs >= patience:
                    print(f"    early stopping at epoch {epoch + 1} "
                          f"(no val improvement for {patience} epochs)")
                    break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


def _eval_loss(model, loader, criterion):
    model.eval()
    total_loss = 0.0
    n = 0
    with torch.no_grad():
        for inputs, labels in loader:
            inputs, labels = inputs.to(DEVICE), labels.to(DEVICE)
            outputs = model(inputs)
            if hasattr(outputs, "logits"):
                outputs = outputs.logits
            loss = criterion(outputs, labels)
            total_loss += loss.item() * inputs.size(0)
            n += inputs.size(0)
    return total_loss / max(n, 1)


def proba_pytorch_model(model, paths) -> np.ndarray:
    """Batch inference: returns an (n, 2) array of softmax probabilities
    [P(Good), P(Damaged)] for a list of image paths, using the deterministic
    (non-augmented) eval transform. Shared by the CNN and ViT wrappers so
    classifier.py can evaluate and soft-vote both the same way. A path that
    fails to open (same transient-I/O risk as during training) falls back to
    a neutral 0.5/0.5 rather than aborting the whole evaluation pass."""
    model.to(DEVICE)
    model.eval()
    out = np.full((len(paths), 2), 0.5)
    with torch.no_grad():
        for i, p in enumerate(paths):
            try:
                img_pil = Image.open(p).convert("RGB")
            except (OSError, FileNotFoundError) as e:
                print(f"[WARN] Skipping unreadable image during evaluation: {Path(p).name} ({e})")
                continue
            x = pytorch_transform(img_pil).unsqueeze(0).to(DEVICE)
            logits = model(x)
            if hasattr(logits, "logits"):
                logits = logits.logits
            out[i] = torch.softmax(logits, dim=1)[0].cpu().numpy()
    return out
