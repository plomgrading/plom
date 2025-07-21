# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
from plom_server.Papers.models import Paper
from plom_server.Papers.services import PaperInfoService
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import pandas as pd
from abc import abstractmethod
from typing import Any, Sequence, Mapping
from PIL import Image
from sklearn.cluster import AgglomerativeClustering
import cv2
from .image_processing_service import ImageProcessingService
import numpy as np
from io import BytesIO
from transformers import TrOCRProcessor
from .embedder import SymbolicEmbedder, TrOCREmbedder
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.decomposition import PCA


class ClusteringModel:
    """Interface for clustering model"""

    @abstractmethod
    def cluster_papers(self, paper_to_image: dict[int, np.ndarray]) -> dict[int, int]:
        """Cluster the given papers

        Args:
            paper_to_image: a dictionary mapping paper number to a (processed) image

        Returns:
            A dictionary mapping the paper number to their cluster id
        """
        pass


class HMEClusteringModel(ClusteringModel):
    def __init__(self):

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        symbolic_model_path = "model_cache/hme_symbolic.pth"
        trocr_model_path = "model_cache/hme_trOCR.pth"
        self.symbolic = SymbolicEmbedder(symbolic_model_path, device)
        self.trOCR = TrOCREmbedder(trocr_model_path, device)

    def get_embeddings(self, img: np.ndarray) -> list:
        """Get the feature vector for the given image that will be used for clustering.

        Args:
            img: the image whose feature vector will be generated and used for clustering.

        Returns:
            a list representing feature used for clustering. In this model, each feature
            represents a probability for a character.
        """
        feat_sym = self.symbolic.embed(img)
        feat_trocr = self.trOCR.embed(img)
        # concatenate on feature‐axis → (N × (D_sym+D_ocr))
        return list(np.concatenate((feat_sym, feat_trocr)))

    def tune_threshold(
        self, X, thresholds=np.linspace(4, 10, 100), metric="silhouette"
    ):
        """
        Try AgglomerativeClustering(distance_threshold=t) for each t in thresholds,
        score it with the chosen metric, and return the best labels + threshold.
        """
        best = {
            "score": -np.inf if metric == "silhouette" else np.inf,
            "threshold": None,
            "labels": None,
        }

        for t in thresholds:
            clustering = AgglomerativeClustering(
                n_clusters=None, metric="euclidean", distance_threshold=t
            )
            labels = clustering.fit_predict(X)
            # need at least 2 clusters to score
            if len(set(labels)) < 2:
                continue

            if metric == "silhouette":
                score = silhouette_score(X, labels)
                # silhouette: higher → better
                if score > best["score"]:
                    best.update(score=score, threshold=t, labels=labels)

            elif metric == "davies":
                score = davies_bouldin_score(X, labels)
                # DB index: lower → better
                if score < best["score"]:
                    best.update(score=score, threshold=t, labels=labels)

        print(f"BEST distance: {best["threshold"]:.2f}")
        return best["labels"]

    def cluster_papers(self, paper_to_image: dict[int, np.ndarray]) -> dict[int, int]:
        """Cluster the given papers

        Args:
            paper_to_image: a dictionary mapping paper number to a (processed) image

        Returns:
            A dictionary mapping the paper number to their cluster id
        """

        # Build feature matrix
        X = np.vstack(
            [self.get_embeddings(image) for pn, image in paper_to_image.items()]
        )
        print(f"SHAPE: {X.shape}")

        X_reduced = PCA(n_components=min(len(paper_to_image), 50)).fit_transform(X)

        # cluster on that matrix
        # clustering_model = AgglomerativeClustering(
        #     n_clusters=None, distance_threshold=7.0, linkage="ward"
        # )

        clusterIDs = self.tune_threshold(X_reduced, np.linspace(4, 10, 100), "davies")
        return dict(zip(list(paper_to_image.keys()), clusterIDs))


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


class MCQClusteringModel(ClusteringModel):

    def __init__(self):
        self.out_features = 11
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Reconstruct the model architecture and load weights
        model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        in_feats = model.fc.in_features
        model.avgpool = AttentionPooling(in_feats)
        model.fc = nn.Linear(in_feats, self.out_features)
        model = model.to(device)

        model.load_state_dict(
            torch.load("model_cache/mcq_model.pth", map_location=device)
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

    def _get_embeddings(self, image: np.ndarray, thresh: float = 0.5):
        """Generate the embeddings (probabilities) for the given image.

        Note: Each feature generated by this model represents a probability.
            Confidence refers to the highest probability for the predictions.

        Args:
            image: the image whose embeddings will be generated
        """
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        x = (
            self.infer_tf(Image.fromarray(image)).unsqueeze(0).to(device)
        )  # shape: [1,3,H,W]

        with torch.no_grad():
            logits = self.model(x)
            probs = torch.softmax(logits, dim=1).cpu().numpy()[0]

        return list(probs)

    def get_embeddings(self, img: np.ndarray) -> list:
        """Get the feature vector for the given image that will be used for clustering.

        Args:
            img: the image whose feature vector will be generated and used for clustering.

        Returns:
            a list representing feature used for clustering. In this model, each feature
            represents a probability for a character.
        """
        # build a structuring element that will bridge any gap ≤ gap_tolerance
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))

        # close small gaps so that what were once multiple components
        # become one big blob in a single connectedComponents call
        closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)

        # merges all “nearby” pieces
        n_labels, _, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)

        # get the probs with highest confidence
        for lab in range(1, n_labels):  # skip background
            x, y, w, h, area = stats[lab]
            if area < 100:
                continue

            crop = img[y : y + h, x : x + w]
            bestConfidence, bestFeatures = 0.0, [0] * self.out_features

            probs = self._get_embeddings(crop)
            confidence = max(probs)
            if confidence > bestConfidence:
                bestConfidence = confidence
                bestFeatures = probs

        return bestFeatures

    def cluster_papers(self, paper_to_image: dict[int, np.ndarray]) -> dict[int, int]:
        """Cluster papers based on written MCQ responses

        Args:
            paper_to_image: a dictionary mapping paper number to the
                cropped region used for clustering.

        Returns:
            A dictionary mapping the paper number to their cluster id
        """

        # Build feature matrix
        X = np.vstack(
            [self.get_embeddings(image) for pn, image in paper_to_image.items()]
        )

        # cluster on that matrix
        clustering_model = AgglomerativeClustering(
            n_clusters=None, distance_threshold=1.0, linkage="ward"
        )

        clusterIDs = clustering_model.fit_predict(X)
        return dict(zip(list(paper_to_image.keys()), clusterIDs))
