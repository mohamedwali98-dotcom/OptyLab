import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import models
from PIL import Image
from sklearn.metrics import accuracy_score
from classifier_utils import MODEL_DIR, DEVICE, ImageDataset, pytorch_transform, train_pytorch_model, evaluate_pytorch_model

MODEL_PATH_CNN = MODEL_DIR / "classifier_cnn.pth"

def train_cnn(paths, labels):
    print("[INFO] Training CNN (ResNet18)...")
    cnn_dataset = ImageDataset(paths, labels, transform=pytorch_transform)
    cnn_loader = DataLoader(cnn_dataset, batch_size=8, shuffle=True)
    
    cnn_model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    num_ftrs = cnn_model.fc.in_features
    cnn_model.fc = nn.Linear(num_ftrs, 2)
    
    train_pytorch_model(cnn_model, cnn_loader, epochs=3)
    torch.save(cnn_model.state_dict(), MODEL_PATH_CNN)
    
    y_cnn, y_pred_cnn = evaluate_pytorch_model(cnn_model, DataLoader(cnn_dataset, batch_size=8))
    acc = accuracy_score(y_cnn, y_pred_cnn)
    return acc

def load_cnn():
    if not MODEL_PATH_CNN.exists():
        return None
    cnn = models.resnet18()
    cnn.fc = nn.Linear(cnn.fc.in_features, 2)
    cnn.load_state_dict(torch.load(MODEL_PATH_CNN, map_location=DEVICE, weights_only=True))
    cnn.to(DEVICE)
    cnn.eval()
    return cnn

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
