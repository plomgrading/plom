# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer


from __future__ import annotations
from Papers.models import ReferenceImage
import cv2 as cv
from io import BytesIO
import numpy as np
from pathlib import Path
from PIL import Image
from tempfile import TemporaryDirectory
from typing import Any, Dict, List
from warnings import warn
import zipfile

from Papers.models import Paper, FixedPage
from Papers.services import PaperInfoService
from plom.scan import rotate


def get_reference_rectangle(version: int, page: int) -> Dict[str, List[float]]:
    """Given the version and page number, return the x/y coords of the qr codes on the reference image.

    Those coords are used to build a reference rectangle, given by the max/min x/y, which, in turn defines a coordinate system on the page.

    Args:
        version: the version of the source pdf to look at.
        page: the number of the page from which to extract the reference rectangle.

    Returns:
        dict: {corner: [x,y]}, where corner is three of NE,SE,NW,SW, and x,y are floats.
    """
    try:
        rimg_obj = ReferenceImage.objects.get(version=version, page_number=page)
    except ReferenceImage.DoesNotExist:
        raise ValueError(f"There is no reference image for v{version} pg{page}.")
    corner_dat = {}
    for cnr in ["NE", "SE", "NW", "SW"]:
        val = rimg_obj.parsed_qr.get(cnr, None)
        if val:
            corner_dat[cnr] = [val["x_coord"], val["y_coord"]]

    return corner_dat


class RectangleExtractor:
    def __init__(self, version: int, page: int):
        self.page_number = page
        self.version = version
        try:
            rimg_obj = ReferenceImage.objects.get(version=version, page_number=page)
        except ReferenceImage.DoesNotExist:
            raise ValueError(f"There is no reference image for v{version} pg{page}.")

        x_coords = []
        y_coords = []
        for cnr in ["NE", "SE", "NW", "SW"]:
            if cnr in rimg_obj.parsed_qr:
                x_coords.append(rimg_obj.parsed_qr[cnr]["x_coord"])
                y_coords.append(rimg_obj.parsed_qr[cnr]["y_coord"])

        # rectangle described by location of the 3 qr-code stamp centres.
        self.LEFT = min(x_coords)
        self.RIGHT = max(x_coords)
        self.TOP = min(y_coords)
        self.BOTTOM = max(y_coords)
        # width and height of the qr-code bounded region
        self.WIDTH = self.RIGHT - self.LEFT
        self.HEIGHT = self.BOTTOM - self.TOP
        # width and height of the actual image
        self.FULL_WIDTH = rimg_obj.width
        self.FULL_HEIGHT = rimg_obj.height

    def _create_affine_transformation_matrix(
        self, qr_dict: dict[str, dict[str, Any]]
    ) -> np.ndarray[Any, Any]:
        """Given QR data for an image, determine the affine transformation needed to correct the image's orientation.

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

    def extract_rect_region(
        self,
        paper_number: int,
        left_f: float,
        top_f: float,
        right_f: float,
        bottom_f: float,
    ) -> bytes:
        """Given an image, get a particular sub-rectangle, after applying an affine transformation to correct it.

        Args:
            paper_number (int): the number of the paper from which to extract the rectangle of the given version, page
            left_f (float): same as top, defining the left boundary
            top_f (float): fractional value in roughly in ``[0, 1]``
                which define the top boundary of the desired subsection of
                the image.
            bottom_f (float): same as top, defining the bottom boundary
            right_f (float): same as top, defining the right boundary

        Returns:
            the bytes of the image in png format
        """
        paper_obj = Paper.objects.get(paper_number=paper_number)
        img_obj = FixedPage.objects.get(
            version=self.version, page_number=self.page_number, paper=paper_obj
        ).image

        pil_img = rotate.pil_load_with_jpeg_exif_rot_applied(img_obj.image_file.path)
        pil_img = pil_img.rotate(img_obj.rotation, expand=True)

        # convert the PIL.Image to OpenCV format
        opencv_img = cv.cvtColor(np.array(pil_img), cv.COLOR_RGB2BGR)

        affine_matrix = self._create_affine_transformation_matrix(img_obj.parsed_qr)
        righted_img = cv.warpAffine(
            opencv_img,
            affine_matrix,
            (self.FULL_WIDTH, self.FULL_HEIGHT),
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
        resulting_img = Image.fromarray(cv.cvtColor(cropped_img, cv.COLOR_BGR2RGB))
        with BytesIO() as fh:
            resulting_img.save(fh, format="png")
            return fh.getvalue()

    def build_zipfile(
        self,
        dest_filename: str | Path,
        left_f: float,
        top_f: float,
        right_f: float,
        bottom_f: float,
    ):
        """Construct a zipfile of the extracted rectangular regions and save in dest_filename.

        Warning: This constructs the pngs for each extracted region in memory, but then saves the resulting (potentially very large) zipfile on disc. This could cause problems if large rectangles are selected from many pages.
        """
        paper_numbers = (
            PaperInfoService().get_paper_numbers_containing_given_page_version(
                self.version, self.page_number, scanned=True
            )
        )

        with zipfile.ZipFile(dest_filename, mode="w") as archive:
            for pn in paper_numbers:
                fname = f"extracted_rectangle_pn{pn}.png"
                dat = self.extract_rect_region(pn, left_f, top_f, right_f, bottom_f)
                archive.writestr(fname, dat)
