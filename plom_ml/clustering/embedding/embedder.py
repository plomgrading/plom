# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from torchvision import transforms  # type: ignore[import]
from abc import ABC, abstractmethod
import numpy as np
from transformers import TrOCRProcessor
from PIL import Image
import cv2
import onnxruntime as ort  # type: ignore[import]


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

    def __init__(self, weight_path, out_features):
        self.out_features = out_features

        # init model
        self.model = ort.InferenceSession(
            weight_path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )

        self.input_name = self.model.get_inputs()[0].name

        # init inference tf
        self.infer_tf = transforms.Compose(
            [
                transforms.Grayscale(num_output_channels=1),
                transforms.Resize((64, 64)),
                transforms.ToTensor(),
                transforms.Normalize(
                    0.5,
                    0.5,
                ),
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

            x_t = self.infer_tf(Image.fromarray(crop)).unsqueeze(0)

            x_np = x_t.numpy().astype(np.float32)

            # onnx session .run returns a list where each entry represents a tensor for
            # an output value (there may be multiple outputs, but in this case there is only one).
            # Therefore, we do [0] to access the only one ouput value in the return list
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
        return np.array(bestFeatures)


class SymbolicEmbedder(Embedder):
    """Embeds images using a ResNet-34 backbone + projection head."""

    def __init__(self, model_path: str):

        # Load model
        self.model = ort.InferenceSession(
            model_path, providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self.input_name = self.model.get_inputs()[0].name

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
        # collapse a singleton channel
        if image.ndim == 3 and image.shape[2] == 1:
            image = image[:, :, 0]

        # ensure uint8
        if image.dtype != np.uint8:
            image = image.astype(np.uint8)

        pil = Image.fromarray(image, mode="L")
        x_t = self.transform(pil).unsqueeze(0)
        x_np = x_t.numpy().astype(np.float32)
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
