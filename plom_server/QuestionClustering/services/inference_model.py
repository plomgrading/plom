import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from pathlib import Path


class AttentionPooling(nn.Module):
    def __init__(self, in_features):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(in_features, 512), nn.Tanh(), nn.Linear(512, 1), nn.Softmax(dim=1)
        )

    def forward(self, x):
        # Input: [batch, channels, height, width]
        batch, channels, h, w = x.size()
        # Flatten spatial dimensions: [batch, channels, h*w]
        flattened = x.view(batch, channels, h * w)
        # Permute: [batch, h*w, channels]
        flattened = flattened.permute(0, 2, 1)
        # Compute attention weights: [batch, h*w, 1]
        attn_weights = self.attention(flattened)
        # Weighted sum: [batch, channels]
        return torch.sum(attn_weights * flattened, dim=1)


class QuestionClusteringModel:
    def __init__(self):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Reconstruct the model architecture and load weights
        model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        in_feats = model.fc.in_features
        model.avgpool = AttentionPooling(in_feats)
        model.fc = nn.Linear(in_feats, 11)
        model = model.to(device)

        model.load_state_dict(
            torch.load("model_cache/model_6.pth", map_location=device)
        )
        model.eval()

        self.infer_tf = transforms.Compose(
            [
                transforms.Grayscale(num_output_channels=1),
                transforms.Resize((64, 64)),
                transforms.ToTensor(),
                transforms.Normalize((0.5,), (0.5,)),
            ]
        )

        self.model = model

    def predict(self, cropped: np.ndarray, thresh: float = 0.5):
        img = Image.fromarray(cropped)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        x = self.infer_tf(img).unsqueeze(0).to(device)  # shape: [1,3,H,W]

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

        idx = probs.argmax()
        conf = float(probs[idx])

        if conf < thresh:
            return conf, []

        return conf, list(probs)
