# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

import torch
import torch.nn as nn
from torchvision import transforms, models  # type: ignore[import]
from abc import ABC, abstractmethod
from typing import Sequence
import numpy as np
from transformers import TrOCRProcessor
from PIL import Image
import cv2


class Embedder(ABC):
    """Abstract class that embeds features to images for ML tasks."""

    @abstractmethod
    def embed(self, image: np.ndarray) -> np.ndarray:
        """Convert image array into a feature matrix.

        Args:
            image: numpy array image whose features to be generated.

        Returns:
            A numpy array of shape (1, D) where D is embedding dimension.
        """
        pass


class SymbolicEmbedder(Embedder):
    """Embeds images using a ResNet-34 backbone + projection head."""

    class _ProjectionHead(nn.Module):
        def __init__(self, in_dim=512, emb_dim=128, num_classes=101):
            super().__init__()
            self.projector = nn.Sequential(
                nn.Linear(in_dim, emb_dim),
                nn.ReLU(),
                nn.Linear(emb_dim, emb_dim),
            )
            self.classifier = nn.Linear(emb_dim, num_classes)
            nn.init.normal_(self.classifier.weight, std=0.01)
            nn.init.constant_(self.classifier.bias, 0)

        def forward(self, features):
            emb = self.projector(features)
            logits = self.classifier(emb)
            return emb, logits

    def __init__(self, model_path: str, device: torch.device):
        self.device = device
        # Build backbone
        backbone = models.resnet34(weights=models.ResNet34_Weights.IMAGENET1K_V1)
        backbone.conv1 = torch.nn.Conv2d(
            1, 64, kernel_size=7, stride=2, padding=3, bias=False
        )
        backbone.fc = torch.nn.Identity()
        self.backbone = backbone.to(self.device).eval()

        # Build projection head
        self.head = (
            self._ProjectionHead(in_dim=512, emb_dim=128, num_classes=229)
            .to(self.device)
            .eval()
        )

        # Load weights
        ckpt = torch.load(model_path, map_location=self.device)
        self.backbone.load_state_dict(ckpt["backbone_state_dict"])
        self.head.load_state_dict(ckpt["head_state_dict"])

        # Inference transform: grayscale resize + to tensor
        self.transform = transforms.Compose(
            [
                transforms.Resize((128, 256)),
                transforms.ToTensor(),  # scales to [0,1]
            ]
        )

    def embed(self, image: np.ndarray) -> np.ndarray:
        """Embed a single grayscale image into a 1D feature vector.

        Args:
            image: np.ndarray of shape (H, W) or (H, W, 1), dtype uint8 or convertible.

        Returns:
            1D np.ndarray of length emb_dim (e.g. 128).
        """
        CUTOFF_PROB = 0.3

        # collapse a singleton channel
        if image.ndim == 3 and image.shape[2] == 1:
            image = image[:, :, 0]
        # ensure uint8
        if image.dtype != np.uint8:
            image = image.astype(np.uint8)

        # to PIL and transform  Tensor [C, H, W]
        pil = Image.fromarray(image, mode="L")
        t = self.transform(pil)  # [1, H, W]  after Grayscale/ToTensor: [1, H, W]
        x = t.unsqueeze(0).to(self.device)  # [1, 1, H, W]

        # forward
        with torch.no_grad():
            feats = self.backbone(x)  #  [1, 512]
            emb, logits = self.head(feats)  #  [1, emb_dim]

        probs = torch.sigmoid(logits).cpu().numpy()[0]

        probs[probs < CUTOFF_PROB] = 0.0
        # squeeze batch and return
        return probs


class TrOCREmbedder(Embedder):
    """Embeds images using an 8-bit TrOCR encoder (last_hidden_state CLS token)."""

    def __init__(self, model_path: str, device: torch.device):
        self.device = device
        # Load TrOCR processor and encoder
        self.processor = TrOCRProcessor.from_pretrained(
            "fhswf/TrOCR_Math_handwritten", use_fast=True
        )
        self.encoder = (
            torch.load(model_path, map_location=device, weights_only=False)
            .to(self.device)
            .eval()
        )

    def embed(self, arr: np.ndarray) -> np.ndarray:
        """Embed a single image via the 8-bit TrOCR encoder's [CLS] token.

        Args:
            arr: np.ndarray of shape (H, W) or (H, W, 3).

        Returns:
            1D numpy array of length D (hidden size of the encoder).
        """
        IMG_SIZE = (512, 256)

        # ensure PIL RGB
        arr = cv2.resize(arr, IMG_SIZE, interpolation=cv2.INTER_AREA)
        pil = Image.fromarray(arr).convert("RGB")

        # produce a single pixel_values tensor [3, H, W]
        pixels = self.processor.image_processor(
            pil, return_tensors="pt"
        ).pixel_values.squeeze(0)

        # add batch dim → [1, 3, H, W], move to device
        x = pixels.unsqueeze(0).to(self.device)

        # forward & grab CLS token
        with torch.no_grad():
            out = self.encoder(x, return_dict=True).last_hidden_state  # (1, seq_len, D)
            cls_token = out[:, 0, :].cpu().numpy()[0]  # (D,)

        return cls_token
