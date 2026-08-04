import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import models
from PIL import Image
from sklearn.metrics import accuracy_score
from classifier_utils import MODEL_DIR, DEVICE, ImageDataset, pytorch_transform, train_pytorch_model, evaluate_pytorch_model

MODEL_PATH_VIT = MODEL_DIR / "classifier_vit.pth"

def train_vit(paths, labels):
    print("[INFO] Training ViT...")
    vit_dataset = ImageDataset(paths, labels, transform=pytorch_transform)
    vit_loader = DataLoader(vit_dataset, batch_size=8, shuffle=True)
    
    vit_model = models.vit_b_16(weights=models.ViT_B_16_Weights.DEFAULT)
    vit_model.heads.head = nn.Linear(vit_model.heads.head.in_features, 2)
    
    train_pytorch_model(vit_model, vit_loader, epochs=2)
    torch.save(vit_model.state_dict(), MODEL_PATH_VIT)
    
    y_vit, y_pred_vit = evaluate_pytorch_model(vit_model, DataLoader(vit_dataset, batch_size=8))
    acc = accuracy_score(y_vit, y_pred_vit)
    return acc

def load_vit():
    if not MODEL_PATH_VIT.exists():
        return None
    vit = models.vit_b_16()
    vit.heads.head = nn.Linear(vit.heads.head.in_features, 2)
    vit.load_state_dict(torch.load(MODEL_PATH_VIT, map_location=DEVICE, weights_only=True))
    vit.to(DEVICE)
    vit.eval()
    return vit

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
