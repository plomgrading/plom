# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from abc import ABC, abstractmethod

import numpy as np
from PIL import Image
from transformers import TrOCRProcessor
import cv2
import onnxruntime as ort  # type: ignore[import]


class Embedder(ABC):
    """Abstract class that generates images embeddings for ML tasks.

    In simple terms: this is the class that uses ML models to generate "some numbers"
    for images such that they can be grouped based on those numbers.
    """

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

    def __init__(self, weight_path, out_features):
        # Hiding this import so torch unneeded unless this class instantiated

        self.out_features = out_features

        # init model
        self.model = ort.InferenceSession(
            weight_path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )

        self.input_name = self.model.get_inputs()[0].name

    def infer_transform(self, img: Image.Image) -> np.ndarray:
        """Mimic torchvision transform preprocessing of rescaling and ToTensor.

        Args:
            img: the image to be transformed into tensor like result

        Returns:
            4D float32 array of shape (1, 1, 64, 64) where:
                - Axis 0: batch dimension (size 1)
                - Axis 1: channel dimension (grayscale, size 1)
                - Axis 2: height (64 pixels)
                - Axis 3: width (64 pixels)
            Values are normalized to [0, 1].
        """
        img = img.resize((64, 64), Image.Resampling.BILINEAR)
        x = np.asarray(img, dtype=np.float32) / 255.0  # HxW
        x = (x - 0.5) / 0.5
        x = x[None, :, :].astype(np.float32)
        return np.expand_dims(x, 0)

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

            x_np = self.infer_transform(Image.fromarray(crop))

            # onnx session .run returns a list where each entry represents a tensor for
            # an output value (there may be multiple outputs, but in this case there is only one).
            # Therefore, we do [0] to access the only one output value in the return list
            logits_all_batches = self.model.run(None, {self.input_name: x_np})[0]

            # The format now then be come [batch, num_classes], but since there is only 1 batch
            # it's [1, num_classes] and we will squeeze the batch dim.
            logits = logits_all_batches[0]

            # convert logits to probability distribution (softmax)
            probs = np.exp(logits) / np.sum(np.exp(logits))

            # Convert to hellinger space for probability distribution clustering
            hellinger = np.sqrt(probs)

            # We are running the inference on potentially more than one blob in the scene.
            # We may hit on noise strokes instead of the real letters, thus we choose to
            # go with the one blob with highest confidence as a letter.
            confidence = max(probs)
            if confidence > bestConfidence:
                bestConfidence = confidence
                bestFeatures = hellinger

        # avoid 0 which can mess up cosine similarity
        clipped = np.clip(bestFeatures, 1e-8, 1)
        return np.array(clipped)


class SymbolicEmbedder(Embedder):
    """Embeds images using a ResNet-34 backbone + projection head."""

    def __init__(self, model_path: str):

        # Load model
        self.model = ort.InferenceSession(
            model_path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self.input_name = self.model.get_inputs()[0].name

    def infer_transform(self, img: Image.Image) -> np.ndarray:
        """Mimic torchvision transform preprocessing of rescaling and ToTensor.

        Args:
            img: the image to be transformed into tensor like result

        Returns: 4D float32 array of shape (1, 1, 128, 256) where:
            - Axis 0: batch dimension (size 1)
            - Axis 1: channel dimension (grayscale, size 1)
            - Axis 2: height (128 pixels)
            - Axis 3: width (256 pixels)
        Values are normalized to [0, 1].
        """
        img = img.resize((256, 128), Image.Resampling.BILINEAR)
        x = np.asarray(img, dtype=np.float32) / 255.0  # HxW
        x = x[None, :, :].astype(np.float32)
        return np.expand_dims(x, 0)

    def embed(self, image: np.ndarray) -> np.ndarray:
        """Embed a single grayscale image into a 1D feature vector.

        Args:
            image: np.ndarray of shape (H, W) or (H, W, 1), dtype uint8 or convertible.

        Returns:
            1D np.ndarray of length emb_dim (e.g. 128).
        """
        # collapse a singleton channel
        if image.ndim == 3 and image.shape[2] == 1:
            image = image[:, :, 0]

        # ensure uint8
        if image.dtype != np.uint8:
            image = image.astype(np.uint8)

        pil = Image.fromarray(image, mode="L")
        x_np = self.infer_transform(pil)
        emb, logits = self.model.run(None, {self.input_name: x_np})
        probs = np.sqrt(1 / (1 + np.exp(-logits)))[0]

        return probs


class TrOCREmbedder(Embedder):
    """Embeds images using an 8-bit TrOCR encoder (last_hidden_state CLS token)."""

    def __init__(self, model_path: str):
        # Load processor for converting images
        self.processor = TrOCRProcessor.from_pretrained(
            "fhswf/TrOCR_Math_handwritten", use_fast=True
        )

        self.model = ort.InferenceSession(
            model_path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self.input_name = self.model.get_inputs()[0].name

    def embed(self, arr: np.ndarray) -> np.ndarray:
        """Embed a single image via the 8-bit TrOCR encoder's [CLS] token.

        Args:
            arr: np.ndarray of shape (H, W) or (H, W, 3).

        Returns:
            1D numpy array of length D (hidden size of the encoder).
        """
        pil = Image.fromarray(arr).convert("RGB")
        x_t = self.processor.image_processor(pil, return_tensors="pt").pixel_values
        x_np = x_t.numpy().astype(np.float32)
        cls_tokens = self.model.run(None, {self.input_name: x_np})[0][0, 0, :]

        return cls_tokens
