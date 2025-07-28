# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from abc import abstractmethod
import numpy as np
from .image_processing_service import ImageProcessingService
import cv2


class Preprocessor:
    """Interface for preprocessing images before being inputted to clustering model."""

    #  every subclass *must* declare which keys (images) it needs
    input_keys: tuple[str, ...]

    @abstractmethod
    def process(self, images: dict[str, np.ndarray]) -> np.ndarray:
        """Takes one or more images to preprocess it into another image for clustering model input.

        Args:
            images: mapping of input name to image array.

        Returns:
            A processed image that is optimized for feature extraction for the clustering model.
        """
        pass


class DiffProcessor(Preprocessor):
    """Handwriting extractor preprocessor through "diffing" reference and scanned page.

    Contains two keys:
        ref: original image.
        scanned: image with handwriting (same context as ref).


    Args:
        dilation_strength: larger value makes reference more dilated, such that it's more
            robust to noise, but more likely to erase student's work.
        invert: set to true to invert the preprocessed output through bitwise_not. Otherwise, there
            is no inversion applied.
    """

    input_keys = ("ref", "scanned")

    def __init__(self, dilation_strength: int, invert: bool):
        self.dilation_strength = dilation_strength
        self.invert = invert

    def process(self, images: dict[str, np.ndarray]) -> np.ndarray:
        """Get the "difference" between reference and scanned pages.

        images:
            Mapping of input names to image arrays, and must have these keys:
                ["ref", "scanned"] as defined in DiffProcessor.input_keys.


        Return:
            An image representing the extracted handwriting from scanned.
        """
        ref = images["ref"]
        scanned = images["scanned"]
        imp = ImageProcessingService()
        diff = imp.get_diff(ref, scanned, self.dilation_strength)
        return cv2.bitwise_not(diff) if self.invert else diff
