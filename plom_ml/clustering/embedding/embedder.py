# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

import torch
from torchvision import transforms  # type: ignore[import]
from abc import ABC, abstractmethod
import numpy as np
from transformers import TrOCRProcessor
from PIL import Image
import cv2

from plom_ml.clustering.model.model_architecture import MCQClusteringNet, HMESymbolicNet


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


class MCQEmbedder(Embedder):
    """Embed images with MCQ Clustering model."""

    def __init__(self, weight_path, device, out_features):
        self.device = device
        self.out_features = out_features

        # init model architecture
        self.model = MCQClusteringNet(out_features)

        # load model weight
        self.model.load_state_dict(torch.load(weight_path, map_location=device))

        self.model.to(device)
        self.model.eval()

        # init inference tf
        self.infer_tf = transforms.Compose(
            [
                transforms.Grayscale(num_output_channels=1),
                transforms.Resize((64, 64)),
                transforms.ToTensor(),
                transforms.Normalize((0.5,), (0.5,)),
            ]
        )

    def embed(self, img: np.ndarray) -> np.ndarray:
        """Convert image array into a feature matrix.

        Args:
            img: numpy array image whose features to be generated.

        Returns:
            A numpy array of shape (1, D) where D is embedding dimension.
        """
        # build a structuring element that will bridge any gap
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))

        # close small gaps so that what were once multiple components
        # become one big blob in a single connectedComponents call
        closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)

        # merges all “nearby” pieces
        n_labels, _, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)

        bestConfidence, bestFeatures = 0.0, [0] * self.out_features

        # get the probs with highest confidence
        for lab in range(1, n_labels):  # skip background
            x, y, w, h, area = stats[lab]
            if area < 100:
                continue

            crop = img[y : y + h, x : x + w]
            bestConfidence, bestFeatures = 0.0, [0] * self.out_features

            infer = (
                self.infer_tf(Image.fromarray(crop)).unsqueeze(0).to(self.device)
            )  # shape: [1,3,H,W]

            with torch.no_grad():
                logits = self.model(infer)
                probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

            confidence = max(probs)
            if confidence > bestConfidence:
                bestConfidence = confidence
                bestFeatures = probs
        return np.array(bestFeatures)


class SymbolicEmbedder(Embedder):
    """Embeds images using a ResNet-34 backbone + projection head."""

    def __init__(self, model_path: str, device: torch.device):
        self.device = device

        # init model architecture
        self.model = HMESymbolicNet()

        # Load weights
        ckpt = torch.load(model_path, map_location=self.device)
        self.model.backbone.load_state_dict(ckpt["backbone_state_dict"])
        self.model.head.load_state_dict(ckpt["head_state_dict"])

        self.model.to(device)
        self.model.eval()

        # init infer_tf
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
            #  [1, 512]
            emb, logits = self.model.forward(x)

        probs = torch.sigmoid(logits).cpu().numpy()[0]

        probs[probs < CUTOFF_PROB] = 0.0
        # squeeze batch and return
        return probs


class TrOCREmbedder(Embedder):
    """Embeds images using an 8-bit TrOCR encoder (last_hidden_state CLS token)."""

    def __init__(self, model_path: str, device: torch.device):
        self.device = device
        # Load processor for converting images into PyTorch tensors
        self.processor = TrOCRProcessor.from_pretrained(
            "fhswf/TrOCR_Math_handwritten", use_fast=True
        )

        # Feed on the processed tensors then output high-dim features
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

        pixels = self.processor.image_processor(pil, return_tensors="pt").pixel_values

        # move to device
        x = pixels.to(self.device)

        # forward & grab CLS token
        with torch.no_grad():
            out = self.encoder(x, return_dict=True).last_hidden_state  # (1, seq_len, D)
            cls_token = out[:, 0, :].cpu().numpy()[0]  # (D,)

        return cls_token
