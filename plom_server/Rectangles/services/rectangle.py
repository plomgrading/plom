# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import cv2 as cv
import imutils
import numpy as np
from PIL import Image
import zipfile

from Papers.models import ReferenceImage
from Papers.models import Paper, FixedPage
from Papers.services import PaperInfoService
from plom.scan import rotate


def get_reference_rectangle(version: int, page: int) -> dict[str, list[float]]:
    """Given the version and page number, return the x/y coords of the qr codes on the reference image.

    Those coords are used to build a reference rectangle, given by the max/min x/y, which, in turn defines a coordinate system on the page.

    Args:
        version: the version of the source pdf to look at.
        page: the number of the page from which to extract the reference rectangle.

    Returns:
        dict: {corner: [x,y]}, where corner is three of NE,SE,NW,SW, and x,y are floats.

    Raises:
        ValueError: no reference image.
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
    """Provides operations on scanned images based on a reference image.

    Instances are particular to a page/version reference image.  They
    stores information and cached calculations about a coordinate system
    in the QR-code locations, enabling information to be looked up in a
    scanned image based on locations chosen from the reference image.
    """

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

        # rectangle described by location of the 3 qr-code stamp centres of the reference image
        self.LEFT = min(x_coords)
        self.RIGHT = max(x_coords)
        self.TOP = min(y_coords)
        self.BOTTOM = max(y_coords)
        # width and height of the qr-code bounded region of the reference image
        self.WIDTH = self.RIGHT - self.LEFT
        self.HEIGHT = self.BOTTOM - self.TOP
        # overall width and height of the actual reference image
        self.FULL_WIDTH = rimg_obj.width
        self.FULL_HEIGHT = rimg_obj.height

    def _get_affine_transformation_matrix_ref_to_scan(
        self, qr_dict: dict[str, dict[str, Any]]
    ) -> None | np.ndarray:
        """Given QR data for an image, determine the affine transformation that maps coords in the reference image to coordinates in the scan image.

        Args:
            qr_dict: the QR information for the image

        Returns:
            The affine transformation matrix for correcting the image, or None if there is insufficient data.
        """
        # We need 3 qr codes in the dict, so if missing SE or SW
        # then  return None
        if "SE" not in qr_dict or "SW" not in qr_dict:
            return None

        if "NW" in qr_dict:
            ref_three_points = np.array(
                [
                    [self.LEFT, self.TOP],
                    [self.LEFT, self.BOTTOM],
                    [self.RIGHT, self.BOTTOM],
                ],
                dtype="float32",
            )
            scan_three_points = np.array(
                [
                    [qr_dict["NW"]["x_coord"], qr_dict["NW"]["y_coord"]],
                    [qr_dict["SW"]["x_coord"], qr_dict["SW"]["y_coord"]],
                    [qr_dict["SE"]["x_coord"], qr_dict["SE"]["y_coord"]],
                ],
                dtype="float32",
            )
        elif "NE" in qr_dict:
            ref_three_points = np.array(
                [
                    [self.RIGHT, self.TOP],
                    [self.LEFT, self.BOTTOM],
                    [self.RIGHT, self.BOTTOM],
                ],
                dtype="float32",
            )
            scan_three_points = np.array(
                [
                    [qr_dict["NE"]["x_coord"], qr_dict["NE"]["y_coord"]],
                    [qr_dict["SW"]["x_coord"], qr_dict["SW"]["y_coord"]],
                    [qr_dict["SE"]["x_coord"], qr_dict["SE"]["y_coord"]],
                ],
                dtype="float32",
            )
        else:
            return None
        # float32 input expected
        return cv.getAffineTransform(ref_three_points, scan_three_points)

    def _get_perspective_transform_scan_to_ref(
        self, ref_rect: dict[str, float], M_r_to_s: np.ndarray
    ) -> np.ndarray:
        """Given the ref-rectangle and the transform from reference-to-scan, compute (essentially) the inverse transform.

        Args:
            ref_rect: the ref-image coords (pixels) of the ref-rectangle given as {'left': px, 'top':px} etc.
            M_r_to_s: the affine transform from ref-image to scan-image as computed via the location of the qr-codes.

        Returns:
            The perspective transformation matrix that takes the rectangle (in scan-image px coords) and maps it back to
            a rectangle with width-height given by reference rectangle (but translated to origin).
        """
        # map the reference rectangle to scan coordinates
        # (sc_x, sc_y) = M @ (r_x,r_y,1)
        # recall np matrix-mul Matrix @ vec, not M*v.
        scan_rect_coords = np.array(
            [
                M_r_to_s
                @ np.array([ref_rect["left"], ref_rect["top"], 1], dtype="float32"),
                M_r_to_s
                @ np.array([ref_rect["right"], ref_rect["top"], 1], dtype="float32"),
                M_r_to_s
                @ np.array([ref_rect["right"], ref_rect["bottom"], 1], dtype="float32"),
                M_r_to_s
                @ np.array([ref_rect["left"], ref_rect["bottom"], 1], dtype="float32"),
            ],
            dtype="float32",
        )
        # TODO - there should be some checks here for what happens
        # when these coords are outside the bounds of the scan image?

        dest_h = ref_rect["bottom"] - ref_rect["top"]
        dest_w = ref_rect["right"] - ref_rect["left"]
        dest_rect_coords = np.array(
            [[0, 0], [dest_w, 0], [dest_w, dest_h], [0, dest_h]], dtype="float32"
        )
        # now build the getPerspectiveTransform from scan-coords back to ref-coords
        return cv.getPerspectiveTransform(scan_rect_coords, dest_rect_coords)

    def extract_rect_region(
        self,
        paper_number: int,
        left_f: float,
        top_f: float,
        right_f: float,
        bottom_f: float,
    ) -> None | bytes:
        """Given an image, get a particular sub-rectangle, after applying an affine transformation to correct it.

        Args:
            paper_number: the number of the paper from which to extract
                the rectangle of the given version, page.
            top_f (float): fractional value in roughly in ``[0, 1]``
                which define the top boundary of the desired subsection of
                the image.  Measured relative to the centres of the QR codes.
            left_f (float): same as top, defining the left boundary.
            bottom_f (float): same as top, defining the bottom boundary.
            right_f (float): same as top, defining the right boundary.

        Returns:
            The bytes of the image in png format, or none if errors.
        """
        # start by getting the scanned image
        paper_obj = Paper.objects.get(paper_number=paper_number)
        img_obj = FixedPage.objects.get(
            version=self.version, page_number=self.page_number, paper=paper_obj
        ).image

        # rectangle to extract in ref-image-coords
        top = round(self.TOP + top_f * self.HEIGHT)
        bottom = round(self.TOP + bottom_f * self.HEIGHT)
        left = round(self.LEFT + left_f * self.WIDTH)
        right = round(self.LEFT + right_f * self.WIDTH)
        ref_rect = {"left": left, "right": right, "top": top, "bottom": bottom}
        rect_height = bottom - top
        rect_width = right - left

        # now build a transformation to map from ref-image-coords to
        # scan-image-coords
        M_r_to_s = self._get_affine_transformation_matrix_ref_to_scan(img_obj.parsed_qr)
        # this can fail if too few qr-codes in scan-image
        # in which case we return a None
        if M_r_to_s is None:
            return None
        # now use that to map the reference-rectangle over to
        # the scan-image and then build the transform that will
        # take that quadrilateral back to a rectangle of same
        # dimensions as the ref-rectangle, but translated to
        # the origin.
        M_s_to_r = self._get_perspective_transform_scan_to_ref(ref_rect, M_r_to_s)
        # now get the scan-image ready to extract the rectangle
        pil_img = rotate.pil_load_with_jpeg_exif_rot_applied(img_obj.image_file.path)
        # Note: this `img_obj.rotation` is (currently) only 0, 90, 180, 270
        # (The small adjustments from true will be handled by warpPerspective)
        pil_img = pil_img.rotate(img_obj.rotation, expand=True)
        # convert PIL format to OpenCV format via numpy array; feels fragile :(
        opencv_img = cv.cvtColor(np.array(pil_img), cv.COLOR_RGB2BGR)
        # now finally extract out the rectangle from the scan image
        extracted_rect_img = cv.warpPerspective(
            opencv_img, M_s_to_r, (rect_width, rect_height)
        )
        # convert the result to a PIL.Image
        resulting_img = Image.fromarray(
            cv.cvtColor(extracted_rect_img, cv.COLOR_BGR2RGB)
        )
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

        Warning: This constructs the pngs for each extracted region in
        memory, but then saves the resulting (potentially very large)
        zipfile on disc. This could cause problems if large rectangles
        are selected from many pages.
        """
        paper_numbers = PaperInfoService.get_paper_numbers_containing_page(
            self.page_number, version=self.version, scanned=True
        )

        with zipfile.ZipFile(dest_filename, mode="w") as archive:
            # TODO: maybe we could avoid the empty zip case by writing a bit
            # of JSON metadata in here, like the coordinates for example.
            for pn in paper_numbers:
                fname = f"extracted_rectangle_pn{pn}.png"
                dat = self.extract_rect_region(pn, left_f, top_f, right_f, bottom_f)
                if dat is None:
                    # TODO: is just ignoring the None's right?  What if they are all Nones
                    # do we make an empty zip?  That's no fun.
                    continue
                archive.writestr(fname, dat)

    def get_largest_rectangle_contour(
        self, region: None | dict[str, float] = None
    ) -> None | dict[str, float]:
        """Helper function for extracting the largest box from an image.

        Args:
            region: part of the image where the largest box is extracted from.

        Returns:
            A dict of the coordinates of the top-left and bottom-right corners of the rectangle
            encoded as {'left_f':blah, 'top_f':blah} etc or `None` if an error occurred. The coordinates
            are relative to positions of the qr-codes, and so values in the interval [0,1] (plus
            some overhang for the margins).
        """
        try:
            rimg_obj = ReferenceImage.objects.get(
                version=self.version, page_number=self.page_number
            )
        except ReferenceImage.DoesNotExist:
            raise ValueError(
                f"There is no reference image for v{self.version} pg{self.page_number}."
            )
        # ref-image into cv image: cannot just use imread b/c of DB abstraction
        img_bytes = rimg_obj.image_file.read()
        raw_bytes_as_1d_array: Any = np.frombuffer(img_bytes, np.uint8)
        src_image = cv.imdecode(raw_bytes_as_1d_array, cv.IMREAD_COLOR)
        if src_image is None:
            raise ValueError(
                f"Could not read reference image v{self.version} pg{self.page_number}."
            )
        # if a region is specified then cut it out from the original image,
        # but we need to remember to map the resulting rectangle back to the
        # original coordinate system.
        # make sure region is padded by a few pixels.
        pad = 16
        if region:
            img_left = max(int(region["left_f"] * self.WIDTH + self.LEFT) - pad, 0)
            img_right = min(
                int(region["right_f"] * self.WIDTH + self.LEFT) + pad, self.FULL_WIDTH
            )
            img_top = max(int(region["top_f"] * self.HEIGHT + self.TOP) - pad, 0)
            img_bottom = min(
                int(region["bottom_f"] * self.HEIGHT + self.TOP) + pad, self.FULL_WIDTH
            )
            src_image = src_image[img_top:img_bottom, img_left:img_right]
        else:
            img_left = 0
            img_top = 0
        # Process the image so as to find the contours.
        # TODO = improve this - it seems pretty clunky.
        # Grey, Blur and Edging are standard processes for text detection.
        grey_image = cv.cvtColor(src_image, cv.COLOR_BGR2GRAY)
        blurred_image = cv.GaussianBlur(grey_image, (3, 3), 0)
        edged_image = cv.Canny(blurred_image, threshold1=5, threshold2=255)
        contours = cv.findContours(
            edged_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE
        )
        contour_lists = imutils.grab_contours(contours)
        sorted_contour_list = sorted(contour_lists, key=cv.contourArea, reverse=True)

        box_contour = None
        for contour in sorted_contour_list:
            perimeter = cv.arcLength(contour, True)
            # Approximate the contour
            third_order_moment = cv.approxPolyDP(contour, 0.02 * perimeter, True)
            # check that the contour is a quadrilateral
            if len(third_order_moment) == 4:
                box_contour = third_order_moment
                break
        if box_contour is not None:
            corners_as_array = box_contour.reshape(4, 2)
            # the box contour will be 4 points - take min/max of x and y to get the corners.
            # this is in image pixels
            left = min([X[0] for X in corners_as_array]) + img_left
            right = max([X[0] for X in corners_as_array]) + img_left
            top = min([X[1] for X in corners_as_array]) + img_top
            bottom = max([X[1] for X in corners_as_array]) + img_top
            # make sure the box is not too small
            if (right - left) < 16 or (bottom - top) < 16:
                return None

            # convert to [0,1] ranges relative to qr code positions
            left_f = (left - self.LEFT) / self.WIDTH
            right_f = (right - self.LEFT) / self.WIDTH
            top_f = (top - self.TOP) / self.HEIGHT
            bottom_f = (bottom - self.TOP) / self.HEIGHT

            return {
                "left_f": left_f,
                "top_f": top_f,
                "right_f": right_f,
                "bottom_f": bottom_f,
            }

        return None
