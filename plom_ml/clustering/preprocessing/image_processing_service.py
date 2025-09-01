# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2025 Colin B. Macdonald

import cv2
import numpy as np

# unsure why pylint complains here: I tried it locally
from skimage.transform import resize  # pylint: disable=no-name-in-module


class ImageProcessingService:
    """Preprocess images services."""

    def addContrast(self, img: np.ndarray, alpha: float, iterations: int) -> np.ndarray:
        """Increase image contrast.

        This operation does not modify original image.

        Args:
            img: the image to manipulate.
            alpha: the strength of constrasting effect, higher value increases
                the contrastive effect.
            iterations: how many times to re-iterate the contrastive effect on the image.
                Higher value has stronger contrastive effect.

        Returns:
            Image (a copy) whose contrast has been manipulated.
        """
        res = img.copy()
        for _ in range(iterations):
            bg = cv2.GaussianBlur(
                res,
                (0, 0),  # kernel (0, 0) auto computes kernel size from sigmas
                sigmaX=15,
                sigmaY=15,
            )
            clean = cv2.addWeighted(res, 1 + alpha, bg, -alpha, 0)
            res = np.clip(clean, 0, 255).astype(np.uint8)
        return res

    def get_connected_component_only(
        self, image: np.ndarray, min_area: int
    ) -> np.ndarray:
        """Filter image to only preserve connected components of min_area.

        This operation is useful to remove noises by only preserving "large enough" blobs.
        The filtered blobs are marked as white (255) while others are marked as black (0).
        This operation does not modify the original image and return a copy.

        Args:
            image: the original image to be manipulated.
            min_area: the minimum area for the blobs to be considered.

        Returns:
            A copy image that has filtered all blobs that have area less than min_area.
        """
        # Compute connected components & stats
        _, labels, stats, _ = cv2.connectedComponentsWithStats(image, connectivity=8)

        # Get all areas
        areas = stats[:, cv2.CC_STAT_AREA]  # shape (n_labels,)

        # Build keep mask and explicitly drop background
        keep = areas >= min_area  # boolean array
        keep[0] = False  # label 0 is background (drop it)

        # Vectorized filtering
        filtered = (keep[labels]).astype(np.uint8) * 255

        return filtered

    def get_diff(
        self, blank_ref: np.ndarray, scanned: np.ndarray, dilation_iteration: int = 1
    ) -> np.ndarray:
        """Get the binarized "difference" between scanned and blank_ref.

        All operations are done in grayscale, if any input image is not grayscale then they
        will be converted to grayscale first. Furthermore, scanned input will be enforced to
        match blank_ref dimension if they are provided with different dimension.

        Args:
            blank_ref: An image that is used as reference.
            scanned: An image that has "stuff" on top of blank_ref that needs
                to be extracted.
            dilation_iteration: higher value makes the extraction less sensitive to noise,
                but increases chances of removing "stuff" from scanned.

        Returns:
            A binarized image of the "difference" between scanned and blank_ref. Pixels
            corresponding to differences are set to 255 (white), while unchanged regions
            are set to 0 (black).
        """
        # bump this to kill more noise, but if too high, it can erase handwriting near answer boxes
        # ideal values sit around 2 - 6
        REF_DILATING_KERN = (4, 4)

        # connected pixels under this area are erased, should be under 70
        # NOTE: For noisy scans, 15 is insufficient, perhaps might want to increase to 30 -50
        # BUT becareful, this might kill small disconnected handwritings.
        BLOB_MIN_AREA = 15

        # Ensure grayscale
        if blank_ref.ndim == 3:
            blank_ref = cv2.cvtColor(blank_ref, cv2.COLOR_BGR2GRAY)

        if scanned.ndim == 3:
            scanned = cv2.cvtColor(scanned, cv2.COLOR_BGR2GRAY)

        # force scanned to be of same dimension as blank_ref
        if blank_ref.shape != scanned.shape:
            scanned = resize(
                scanned,
                (blank_ref.shape[0], blank_ref.shape[1]),
                anti_aliasing=True,
                preserve_range=True,
            ).astype(np.uint8)

        # convert ref to inverted binary
        _, binarized_ref = cv2.threshold(
            blank_ref, thresh=230, maxval=255, type=cv2.THRESH_BINARY_INV
        )

        # dilate the inks in ref
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, REF_DILATING_KERN)
        dilated_ref = cv2.dilate(binarized_ref, kernel, iterations=dilation_iteration)

        # increase scanned image contrast so faint handwriting is not lost
        addedContrast = self.addContrast(scanned, alpha=2, iterations=2)
        detail = cv2.GaussianBlur(addedContrast, (0, 0), sigmaX=1.5)
        sharp = cv2.addWeighted(addedContrast, 1.0, detail, -0.2, 0)

        # binarize scanned
        binarized_scanned = cv2.adaptiveThreshold(
            sharp,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=25,
            C=20,
        )

        # Remove noises from scanned image
        temp = cv2.morphologyEx(binarized_scanned, cv2.MORPH_OPEN, np.ones((2, 2)))
        cleaned_scanned = cv2.morphologyEx(temp, cv2.MORPH_CLOSE, np.ones((1, 2)))
        filtered = self.get_connected_component_only(
            cleaned_scanned, min_area=BLOB_MIN_AREA
        )

        # Get the diff between ref and scanned
        diff = cv2.bitwise_and(filtered, cv2.bitwise_not(dilated_ref))

        # cleanup noises post-diffing
        cleaned = cv2.morphologyEx(diff, cv2.MORPH_OPEN, np.ones((2, 2)))
        final = self.get_connected_component_only(cleaned, min_area=BLOB_MIN_AREA)

        return final
