# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

# sklearn
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.decomposition import PCA

# plom_ml
from .embedder import SymbolicEmbedder, TrOCREmbedder
from sklearn.cluster import AgglomerativeClustering

# torch
import torch
import torch.nn as nn
from torchvision import models, transforms

# misc
from PIL import Image
from abc import abstractmethod
import cv2
import numpy as np
import yaml
import os


class ClusteringModel:
    """Interface for clustering model.

    This interface enforces cluster_papers method which enforces clustering functionality
    with uniform input and output formats.
    """

    @abstractmethod
    def cluster_papers(self, paper_to_image: dict[int, np.ndarray]) -> dict[int, int]:
        """Cluster the given papers into a mapping of paper_num to clusterId.

        This method directly calls inference models on the provided images. Therefore, if
        there are expected preprocessing steps the images must be preprocessed before
        feeding them into this function.

        Args:
            paper_to_image: a dictionary mapping paper number to a (processed) image

        Returns:
            A dictionary mapping the paper number to their cluster id.
        """
        pass


class HMEClusteringModel(ClusteringModel):
    """Handwritten math expression model."""

    def __init__(self):

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # load model config
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # load models weight
        symbolic_model_path = config["models"]["hme"]["symbolic"]
        trocr_model_path = config["models"]["hme"]["trocr"]

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

    def get_best_clustering(
        self, X: np.ndarray, thresholds: list[float], metric="silhouette"
    ) -> np.ndarray:
        """Get the best clustering of X by searching for optimal threshold that maximizes the metric.

        This function defaults with AgglomerativeClustering clustering algorithm.

        Args:
            X: the feature matrix.
            thresholds: the choices of distance thresholds.
            metric: which metric to optimize. Currently supports: "silhouette" and "davies".

        Returns:
            A numpy array of clusterId where the order matches with the
            inputs (index 0 provides Id for row 0 of X)
        """
        best_score = -np.inf if metric == "silhouette" else np.inf
        best_labels = np.array([])

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
                # silhouette: higher -> better
                if score > best_score:
                    best_score = score
                    best_labels = labels

            elif metric == "davies":
                score = davies_bouldin_score(X, labels)
                # DB index: lower -> better
                if score < best_score:
                    best_score = score
                    best_labels = labels

        return best_labels

    def cluster_papers(self, paper_to_image: dict[int, np.ndarray]) -> dict[int, int]:
        """Cluster the given papers.

        Args:
            paper_to_image: a dictionary mapping paper number to a (processed) image.

        Returns:
            A dictionary mapping the paper number to their cluster id.
        """
        # Build feature matrix
        X = np.vstack(
            [self.get_embeddings(image) for pn, image in paper_to_image.items()]
        )

        X_reduced = PCA(n_components=min(len(paper_to_image), 50)).fit_transform(X)

        # set up distance threshold search space
        min_thresh = 4
        max_thresh = 10
        thresh_counts = 100
        thresholds = [
            float(t) for t in np.linspace(min_thresh, max_thresh, thresh_counts)
        ]

        clusterIDs = self.get_best_clustering(X_reduced, thresholds, "davies")
        return dict(zip(list(paper_to_image.keys()), clusterIDs))


class MCQClusteringModel(ClusteringModel):
    """Handwritten MCQ clustering model."""

    class _AttentionPooling(nn.Module):
        """Layer for attention pooling."""

        def __init__(self, in_features):
            super().__init__()
            self.attention = nn.Sequential(
                nn.Linear(in_features, 512),
                nn.Tanh(),
                nn.Linear(512, 1),
                nn.Softmax(dim=1),
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

    def __init__(self):
        self.out_features = 11
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Reconstruct the model architecture and load weights
        model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        model.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        in_feats = model.fc.in_features
        model.avgpool = self._AttentionPooling(in_feats)
        model.fc = nn.Linear(in_feats, self.out_features)
        model = model.to(device)

        # load model config
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # load model weight
        mcq_model_path = config["models"]["mcq"]
        model.load_state_dict(torch.load(mcq_model_path, map_location=device))
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

    def _get_embeddings(self, image: np.ndarray):
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

        bestConfidence, bestFeatures = 0.0, [0] * self.out_features

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
        """Cluster papers based on handwritten MCQ.

        Args:
            paper_to_image: a dictionary mapping paper number to the
                cropped region used for clustering.

        Returns:
            A dictionary mapping the paper number to their cluster id
        """
        # Build feature matrix
        X = np.vstack(
            [self.get_embeddings(image) for _, image in paper_to_image.items()]
        )

        # cluster on that matrix
        clustering_model = AgglomerativeClustering(
            n_clusters=None, distance_threshold=1.0, linkage="ward"
        )

        clusterIDs = clustering_model.fit_predict(X)
        return dict(zip(list(paper_to_image.keys()), clusterIDs))
