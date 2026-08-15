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

MODEL_PATH_CNN = MODEL_DIR / "classifier_cnn.pth"

def train_cnn(paths, labels, val_paths=None, val_labels=None):
    """Fine-tune ResNet18 on the given training split. If a validation split
    is provided, training uses early stopping / best-checkpoint on val loss
    instead of unconditionally keeping the last epoch. Returns the trained
    model; weights are also saved to disk as before."""
    print("[INFO] Training CNN (ResNet18)...")
    train_dataset = ImageDataset(paths, labels, transform=train_transform)
    train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True)

    val_loader = None
    if val_paths:
        val_dataset = ImageDataset(val_paths, val_labels, transform=pytorch_transform)
        val_loader = DataLoader(val_dataset, batch_size=8)

    cnn_model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    num_ftrs = cnn_model.fc.in_features
    cnn_model.fc = nn.Linear(num_ftrs, 2)

    train_pytorch_model(
        cnn_model, train_loader, val_loader=val_loader, epochs=8,
        head_params=cnn_model.fc.parameters(),
        lr_head=1e-3, lr_backbone=1e-4,
        class_weights=class_weights_for(labels),
    )
    torch.save(cnn_model.state_dict(), MODEL_PATH_CNN)
    return cnn_model

def load_cnn():
    if not MODEL_PATH_CNN.exists():
        return None
    cnn = models.resnet18()
    cnn.fc = nn.Linear(cnn.fc.in_features, 2)
    cnn.load_state_dict(torch.load(MODEL_PATH_CNN, map_location=DEVICE, weights_only=True))
    cnn.to(DEVICE)
    cnn.eval()
    return cnn

def proba_cnn(model, paths) -> np.ndarray:
    return proba_pytorch_model(model, paths)

def predict_cnn(model, img_path):
    img_pil = Image.open(img_path).convert("RGB")
    cnn_input = pytorch_transform(img_pil).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        out = model(cnn_input)
        prob = torch.softmax(out, dim=1)[0]
        label_idx = torch.argmax(prob).item()
        conf = float(prob[label_idx])
        pred = "Good" if label_idx == 0 else "Damaged"
    return pred, conf
