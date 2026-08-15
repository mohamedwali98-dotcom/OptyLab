import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import models
from PIL import Image
import numpy as np
from classifier_utils import (
    MODEL_DIR, DEVICE, ImageDataset, pytorch_transform, train_transform,
    train_pytorch_model, proba_pytorch_model, class_weights_for,
)

MODEL_PATH_VIT = MODEL_DIR / "classifier_vit.pth"

def train_vit(paths, labels, val_paths=None, val_labels=None):
    """Fine-tune ViT-B/16 on the given training split. ViT is far more prone
    to catastrophic forgetting than the CNN when fully fine-tuned at a high
    learning rate, so the backbone gets a much lower LR than the head (this
    is what the old fixed lr=1e-3-for-everything run was under-training at
    ~68% accuracy). If a validation split is provided, training uses early
    stopping / best-checkpoint on val loss. Returns the trained model."""
    print("[INFO] Training ViT...")
    train_dataset = ImageDataset(paths, labels, transform=train_transform)
    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)

    val_loader = None
    if val_paths:
        val_dataset = ImageDataset(val_paths, val_labels, transform=pytorch_transform)
        val_loader = DataLoader(val_dataset, batch_size=8)

    vit_model = models.vit_b_16(weights=models.ViT_B_16_Weights.DEFAULT)
    vit_model.heads.head = nn.Linear(vit_model.heads.head.in_features, 2)

    train_pytorch_model(
        vit_model, train_loader, val_loader=val_loader, epochs=6,
        head_params=vit_model.heads.head.parameters(),
        lr_head=1e-3, lr_backbone=1e-5,
        class_weights=class_weights_for(labels),
    )
    torch.save(vit_model.state_dict(), MODEL_PATH_VIT)
    return vit_model

def load_vit():
    if not MODEL_PATH_VIT.exists():
        return None
    vit = models.vit_b_16()
    vit.heads.head = nn.Linear(vit.heads.head.in_features, 2)
    vit.load_state_dict(torch.load(MODEL_PATH_VIT, map_location=DEVICE, weights_only=True))
    vit.to(DEVICE)
    vit.eval()
    return vit

def proba_vit(model, paths) -> np.ndarray:
    return proba_pytorch_model(model, paths)

def predict_vit(model, img_path):
    img_pil = Image.open(img_path).convert("RGB")
    vit_input = pytorch_transform(img_pil).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        out = model(vit_input)
        prob = torch.softmax(out, dim=1)[0]
        label_idx = torch.argmax(prob).item()
        conf = float(prob[label_idx])
        pred = "Good" if label_idx == 0 else "Damaged"
    return pred, conf
