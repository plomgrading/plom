# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from abc import abstractmethod
import numpy as np
from .image_processing_service import ImageProcessingService
from plom_server.QuestionClustering.models import ClusteringModelType
import cv2


class Preprocessor:
    """Interface for preprocess images before being inputted to clustering model"""

    @abstractmethod
    def process(self, *imgs: np.ndarray) -> np.ndarray:
        """Takes one or more images to preprocess it into another image for clustering model input

        Returns:
            A processed image that is more optimized for feature extraction for the clustering model
        """
        pass


class DiffProcessor(Preprocessor):
    """Handwriting extractor preprocessor.

    Args:
        dilation_strength: larger value makes reference more dilated, such that it's more
            robust to noise, but more likely to erase student's work.
    """

    def __init__(self, dilation_strength: int, invert: bool):
        self.dilation_strength = dilation_strength
        self.invert = invert

    def process(self, ref: np.ndarray, scanned: np.ndarray) -> np.ndarray:
        """Get the "difference" between reference and scanned pages.

        Args:
            ref: the original page.
            scanned: the scanned page.

        Return:
            An image representing the extracted handwriting from scanned.
        """
        imp = ImageProcessingService()
        diff = imp.get_diff(ref, scanned, self.dilation_strength)
        return cv2.bitwise_not(diff) if self.invert else diff
