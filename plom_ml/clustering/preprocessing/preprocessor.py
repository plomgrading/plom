# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from abc import abstractmethod
from typing import Mapping

import numpy as np
import cv2

from plom_ml.clustering.exceptions import MissingRequiredInputKeys
from .image_processing_service import ImageProcessingService


class Preprocessor:
    """Interface for preprocessing images before being inputted to clustering model.

    Every subclass must implement input_keys class attribute, which defines what input images are
    required for each preprocessing. Subclass must also implements _process method which controls the
    internal logic of preprocessing post-validation.
    """

    # define which keys (images) it needs
    input_keys: set[str]

    def __init_subclass__(cls):
        """Enfoce every subclass MUST declare input_keys."""
        super().__init_subclass__()
        if not hasattr(cls, "input_keys") or not isinstance(cls.input_keys, set):
            raise TypeError(
                f"{cls.__name__} must define a class-level `input_keys: set[str]`."
            )

    def _validate(self, images: Mapping[str, np.ndarray]) -> None:
        """Validate images for processing.

        Currently ensures images must contain the keys defined in each subclass's input_keys.
        Note that it does not enforce the keys must exactly the same as input_keys.

        Args:
            images: mapping of input name to image array.

        Raises:
            MissingRequiredInputKeys: images don't have certain keys defined in input_keys.
        """
        missing_keys = self.input_keys - images.keys()

        if missing_keys:
            raise MissingRequiredInputKeys(
                f"image inputs are missing these keys: {missing_keys}"
            )

    @abstractmethod
    def _process(self, images: Mapping[str, np.ndarray]) -> np.ndarray:
        """Internal logic of preprocessing post-validated images.

        Args:
            images: mapping of input name to image array.

        Returns:
            A processed image that is optimized for feature extraction for the clustering model.
        """
        pass

    def process(self, images: Mapping[str, np.ndarray]) -> np.ndarray:
        """Takes one or more images to preprocess it into another image for clustering model input.

        Args:
            images: mapping of input name to image array.

        Returns:
            A processed image that is optimized for feature extraction for the clustering model.
        """
        self._validate(images)
        return self._process(images)


class DiffProcessor(Preprocessor):
    """Handwriting extractor preprocessor through "diffing" reference and scanned page.

    Each processing must provide these keys:
        ref: original image.
        scanned: image with handwriting (same context as ref).


    Args:
        dilation_strength: larger value makes reference more dilated, such that it's more
            robust to noise, but more likely to erase student's work.
        invert: set to true to invert the preprocessed output through bitwise_not. Otherwise, there
            is no inversion applied.
    """

    input_keys = {"ref", "scanned"}

    def __init__(self, dilation_strength: int, invert: bool):
        self.dilation_strength = dilation_strength
        self.invert = invert

    def _process(self, images: Mapping[str, np.ndarray]) -> np.ndarray:
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
