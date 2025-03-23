# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov

from warnings import warn
from typing import Any

import cv2 as cv
import numpy as np
from pathlib import Path
from PIL import Image

from plom.scan import rotate


class PageImageProcessor:
    """Functions for processing a page-image: rotation.

    (TODO: gamma correction, etc?)
    """

    # values used for QR code centre locations and page dimensions
    # obtained by running QRextract on un-rotated demo page images
    TOP = 139.5
    BOTTOM = 1861.5
    RIGHT = 1419.5
    LEFT = 126.5
    PWIDTH = 1546
    PHEIGHT = 2000

    # dimensions of the QR-bounded region
    WIDTH = RIGHT - LEFT
    HEIGHT = BOTTOM - TOP

    def get_page_orientation(self, qr_code_data: dict[str, dict[str, Any]]) -> str:
        """Return a string representing a page orientation.

        The choices are:
            upright: page doesn't need to be rotated
            upside_down: page should be rotated 180 degrees
            turned_left: page should be rotated -90 degrees
            turned_right: page should be rotated 90 degrees

        The "expected" quadrants are the "quadrant" values in qr_code_data,
        and are labelled 1-4. The "actual" quadrants are the keys in qr_code_data,
        and are labelled NW, NE, SW, SE:

        upright:
            2---1   NW---NE
            |   |    |   |
            |   |    |   |
            3---4   SW---SE

        turned_right:
            3------2    NW---NE
            |      |     |   |
            4------1     |   |
                        SW---SE

        turned_left:
            1------4    NW---NE
            |      |     |   |
            2------3     |   |
                        SW---SE

        upside_down:
            4---3    NW---NE
            |   |     |   |
            |   |     |   |
            1---2    SW---SE

        Args:
            qr_code_data: data parsed from page-image QR codes.

        Returns:
            str: short description of the orientation.

        Raises:
            RuntimeError: something inconsistent in the QR data.
        """
        northeast_orientation = None
        if "NE" in qr_code_data:
            expected_corner = qr_code_data["NE"]["quadrant"]
            northeast_orientation = self._check_corner(
                val_from_qr=expected_corner,
                upright="1",
                turned_right="2",
                turned_left="4",
                upside_down="3",
            )

        northwest_orientation = None
        if "NW" in qr_code_data:
            expected_corner = qr_code_data["NW"]["quadrant"]
            northwest_orientation = self._check_corner(
                val_from_qr=expected_corner,
                upright="2",
                turned_right="3",
                turned_left="1",
                upside_down="4",
            )

        southeast_orientation = None
        if "SE" in qr_code_data:
            expected_corner = qr_code_data["SE"]["quadrant"]
            southeast_orientation = self._check_corner(
                val_from_qr=expected_corner,
                upright="4",
                turned_right="1",
                turned_left="3",
                upside_down="2",
            )

        southwest_orientation = None
        if "SW" in qr_code_data:
            expected_corner = qr_code_data["SW"]["quadrant"]
            southwest_orientation = self._check_corner(
                val_from_qr=expected_corner,
                upright="3",
                turned_right="4",
                turned_left="2",
                upside_down="1",
            )

        # make sure at least one corner is truthy, and they all agree
        truthy_results = [
            corner
            for corner in [
                northeast_orientation,
                northwest_orientation,
                southwest_orientation,
                southeast_orientation,
            ]
            if corner
        ]

        result_vals = set(truthy_results)
        if len(result_vals) != 1:
            raise RuntimeError("Unable to determine page orientation.")

        return truthy_results[0]

    def _check_corner(
        self,
        val_from_qr: str,
        upright: str,
        turned_right: str,
        turned_left: str,
        upside_down: str,
    ) -> str:
        """Check a page corner for its actual orientation.

        Args:
            val_from_qr (str): one of "1", "2", "3", "4"
            upright (str): the quadrant value for an upright orientation,
                           one of "1", "2", "3", "4"
            turned_right (str): value for a turned_right orientation
            turned_left (str): value for a turned_left orientation
            upside_down (str): value for an upside_down orientation

        Returns:
            String describing the orientation.
        """
        if val_from_qr == upright:
            return "upright"
        elif val_from_qr == turned_right:
            return "turned_right"
        elif val_from_qr == turned_left:
            return "turned_left"
        elif val_from_qr == upside_down:
            return "upside_down"
        raise RuntimeError("Tertium non datur")

    def get_rotation_angle_from_QRs(self, qr_data: dict[str, dict[str, Any]]) -> int:
        """Get the current orientation of a page-image using its parsed QR code data.

        If it isn't upright, return the angle by which the image needs to be rotated,
        in degrees counter-clockwise.

        Args:
            qr_data: parsed QR code data.

        Returns:
            Rotation angle by which the page needs to be rotated.
            If page is already upright, rotation angle of 0 is returned.

        Raises:
            RuntimeError: something inconsistent in the QR data.
        """
        orientation = self.get_page_orientation(qr_data)

        if orientation == "upright":
            return 0

        if orientation == "turned_right":
            rotate_angle = 90
        elif orientation == "turned_left":
            rotate_angle = -90
        else:
            rotate_angle = 180

        return rotate_angle

    def get_rotation_angle_or_None_from_QRs(
        self, qr_data: dict[str, dict[str, Any]]
    ) -> int | None:
        """Get the current orientation or None of a page-image using its parsed QR code data.

        If it isn't upright, return the angle by which the image needs to be rotated,
        in degrees counter-clockwise.

        Args:
            qr_data: parsed QR code data.

        Returns:
            Rotation angle by which the page needs to be rotated.
            If page is already upright, rotation angle of 0 is returned.
            Returns None if the orientation cannot be determined.
            See also also ``get_page_orientation``, although these two
            methods should perhaps converge in the future (TODO).
        """
        try:
            return self.get_rotation_angle_from_QRs(qr_data)
        except RuntimeError:
            # We cannot get the page orientation
            return None

    def create_affine_transformation_matrix(
        self, qr_dict: dict[str, dict[str, Any]]
    ) -> np.ndarray:
        """Given QR data for an image, determine the affine transformation needed to correct the image's orientation.

        TODO: this is likely dead code.

        Args:
            qr_dict (dict): the QR information for the image

        Returns:
            numpy.ndarray: the affine transformation matrix for correcting the image
        """
        if "NW" in qr_dict:
            dest_three_points = np.array(
                [
                    [self.LEFT, self.TOP],
                    [self.LEFT, self.BOTTOM],
                    [self.RIGHT, self.BOTTOM],
                ]
            )
            src_three_points = np.array(
                [
                    [qr_dict["NW"]["x_coord"], qr_dict["NW"]["y_coord"]],
                    [qr_dict["SW"]["x_coord"], qr_dict["SW"]["y_coord"]],
                    [qr_dict["SE"]["x_coord"], qr_dict["SE"]["y_coord"]],
                ]
            )
        elif "NE" in qr_dict:
            dest_three_points = np.array(
                [
                    [self.RIGHT, self.TOP],
                    [self.LEFT, self.BOTTOM],
                    [self.RIGHT, self.BOTTOM],
                ]
            )
            src_three_points = np.array(
                [
                    [qr_dict["NE"]["x_coord"], qr_dict["NE"]["y_coord"]],
                    [qr_dict["SW"]["x_coord"], qr_dict["SW"]["y_coord"]],
                    [qr_dict["SE"]["x_coord"], qr_dict["SE"]["y_coord"]],
                ]
            )
        else:
            return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        # float32 input expected
        return cv.getAffineTransform(
            src_three_points.astype(np.float32),
            dest_three_points.astype(np.float32),
        )

    def extract_rect_region_TODO_REMOVE(
        self,
        image_path: str | Path,
        orientation: int,
        qr_dict: dict[Any, Any],
        top_f: float,
        bottom_f: float,
        left_f: float,
        right_f: float,
    ) -> Image.Image:
        """Given an image, get a particular sub-rectangle, after applying an affine transformation to correct it.

        TODO: this is likely dead code, use Rectangle.extract_rect_region instead?

        Args:
            image_path (str/pathlib.Path): path to image file
            orientation (): a pre-rotation to be applied before calculating
                the affine transform.
            qr_dict (dict): parsed QR code data, used to calculate the
                transformation.
            top_f (float): fractional value in roughly in ``[0, 1]``
                which define the top boundary of the desired subsection of
                the image.
            left_f (float): same as top, defining the left boundary
            bottom_f (float): same as top, defining the bottom boundary
            right_f (float): same as top, defining the right boundary

        Returns:
            PIL.Image: the requested subsection of the original image, or
            the full, righted image if an invalid box range is specified.
        """
        pil_img = rotate.pil_load_with_jpeg_exif_rot_applied(image_path)
        pil_img = pil_img.rotate(orientation, expand=True)

        # convert the PIL.Image to OpenCV format
        opencv_img = cv.cvtColor(np.array(pil_img), cv.COLOR_RGB2BGR)

        affine_matrix = self.create_affine_transformation_matrix(qr_dict)
        righted_img = cv.warpAffine(
            opencv_img,
            affine_matrix,
            (self.PWIDTH, self.PHEIGHT),
            flags=cv.INTER_LINEAR,
        )

        top = round(self.TOP + top_f * self.HEIGHT)
        bottom = round(self.TOP + bottom_f * self.HEIGHT)
        left = round(self.LEFT + left_f * self.WIDTH)
        right = round(self.LEFT + right_f * self.WIDTH)

        if top < 0:
            warn(f"Top input of {top} is outside of image pixel range, capping at 0.")
        top = max(top, 0)
        if left < 0:
            warn(f"Left input of {left} is outside of image pixel range, capping at 0.")
        left = max(left, 0)
        if right > pil_img.width:
            warn(
                f"Right input of {right} is outside of image pixel range,"
                f" capping at {pil_img.width}."
            )
        right = min(right, pil_img.width)
        if bottom > pil_img.height:
            warn(
                f"Bottom input of {bottom} is outside of image pixel range,"
                f" capping at {pil_img.height}."
            )
        bottom = min(bottom, pil_img.height)

        cropped_img = righted_img[top:bottom, left:right]

        # convert the result to a PIL.Image
        result = Image.fromarray(cv.cvtColor(cropped_img, cv.COLOR_BGR2RGB))
        return result
