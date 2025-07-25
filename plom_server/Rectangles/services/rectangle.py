# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024-2025 Andrew Rechnitzer

from io import BytesIO
from math import ceil, floor
from pathlib import Path
from typing import Any

import cv2 as cv
import imutils
import numpy as np
import zipfile
from PIL import Image

from plom_server.Papers.models import ReferenceImage
from plom_server.Papers.models import Paper, FixedPage
from plom_server.Papers.services import PaperInfoService
from plom.scan import rotate


def get_reference_qr_coords_for_page(
    page: int, *, version: int
) -> dict[str, list[float]]:
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
    for cnr in ("NE", "SE", "NW", "SW"):
        val = rimg_obj.parsed_qr.get(cnr, None)
        if val:
            corner_dat[cnr] = [val["x_coord"], val["y_coord"]]

    return corner_dat


def get_reference_rectangle_from_QR_data(
    parsed_qr: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """The reference rectangle is based on the centres of the QR codes."""
    x_coords = []
    y_coords = []
    for cnr in ("NE", "SE", "NW", "SW"):
        if cnr in parsed_qr:
            x_coords.append(parsed_qr[cnr]["x_coord"])
            y_coords.append(parsed_qr[cnr]["y_coord"])
    return {
        "left": min(x_coords),
        "right": max(x_coords),
        "top": min(y_coords),
        "bottom": max(y_coords),
    }


def get_reference_rectangle_for_page(page: int, *, version: int) -> dict[str, float]:
    """The reference rectangle for a particular version and page, based on the centres of the QR codes."""
    try:
        rimg_obj = ReferenceImage.objects.get(version=version, page_number=page)
    except ReferenceImage.DoesNotExist:
        raise ValueError(f"There is no reference image for v{version} pg{page}.")
    return get_reference_rectangle_from_QR_data(rimg_obj.parsed_qr)


def _get_affine_transf_matrix_ref_to_QR_target(
    reference_region: tuple[float, float, float, float],
    qr_dict: dict[str, dict[str, Any]],
) -> None | np.ndarray:
    """Given QR data for a target image, determine the affine transformation that maps coords in the reference image to coordinates in the target.

    Args:
        reference_region: the corners of the reference region in the
            "source" or "ref" image.  Typically, the QR-code locations
            in the reference ("input") image.
        qr_dict: the QR information for the target or scanned image.

    Returns:
        The affine transformation matrix for correcting the image, or None if there is insufficient data.
    """
    LEFT, TOP, RIGHT, BOTTOM = reference_region

    # We need 3 qr codes in the dict, so if missing SE or SW
    # then  return None
    if "SE" not in qr_dict or "SW" not in qr_dict:
        return None

    if "NW" in qr_dict:
        ref_three_points = np.array(
            [
                [LEFT, TOP],
                [LEFT, BOTTOM],
                [RIGHT, BOTTOM],
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
                [RIGHT, TOP],
                [LEFT, BOTTOM],
                [RIGHT, BOTTOM],
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
    ref_rect: dict[str, float], M_r_to_s: np.ndarray
) -> np.ndarray:
    """Given the ref-rectangle and the transform from reference-to-scan, compute (essentially) the inverse transform.

    Args:
        ref_rect: the ref-image coords (pixels, but can be floats)
            of the ref-rectangle given as {'left': px, 'top':px} etc.
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


def extract_rect_region_from_image(
    img: Path,
    qr_dict: dict[str, dict[str, Any]],
    left_f: float,
    top_f: float,
    right_f: float,
    bottom_f: float,
    reference_region: tuple[int | float, int | float, int | float, int | float],
    *,
    pre_rotation: int = 0,
) -> None | bytes:
    """Given an image, get a particular sub-rectangle, after applying an affine transformation to correct it.

    Args:
        img: A path to an image, we will read from it, not write to it.
            TODO: in the future maybe a django "FieldField", which has
            restrictions because we don't want to assume what storage it uses.
        qr_dict: the QR information for the image.
        left_f: fractional value in roughly in ``[0, 1]`` which define
            the left boundary of the desired subsection of the image.
            Measured relative to the ``reference_region`` which is
            typically the centres of the QR codes.
        top_f: similarly defining the top boundary.
        right_f: similarly defining the right boundary.
        bottom_f: similarly defining the bottom boundary.
        reference_region: TODO.

    Keyword Args:
        pre_rotation: TODO.

    Returns:
        The bytes of the image in png format, or none if errors.

    Raises:
        TODO
    """
    LEFT, TOP, RIGHT, BOTTOM = reference_region
    WIDTH = RIGHT - LEFT
    HEIGHT = BOTTOM - TOP

    # rectangle to extract in ref-image-coords
    top = TOP + top_f * HEIGHT
    bottom = TOP + bottom_f * HEIGHT
    left = LEFT + left_f * WIDTH
    right = LEFT + right_f * WIDTH
    ref_rect = {"left": left, "right": right, "top": top, "bottom": bottom}
    rect_height_int = round(bottom - top)
    rect_width_int = round(right - left)

    # now build a transformation to map from ref-image-coords to
    # scan-image-coords
    M_r_to_s = _get_affine_transf_matrix_ref_to_QR_target(reference_region, qr_dict)
    # this can fail if too few qr-codes in scan-image
    # in which case we return a None
    if M_r_to_s is None:
        return None
    # now use that to map the reference-rectangle over to
    # the scan-image and then build the transform that will
    # take that quadrilateral back to a rectangle of same
    # dimensions as the ref-rectangle, but translated to
    # the origin.
    M_s_to_r = _get_perspective_transform_scan_to_ref(ref_rect, M_r_to_s)
    # now get the scan-image ready to extract the rectangle
    pil_img = rotate.pil_load_with_jpeg_exif_rot_applied(img)
    # Note: this `img_obj.rotation` is (currently) only 0, 90, 180, 270
    # (The small adjustments from true will be handled by warpPerspective)
    pil_img = pil_img.rotate(pre_rotation, expand=True)
    # convert PIL format to OpenCV format via numpy array; feels fragile :(
    opencv_img = cv.cvtColor(np.array(pil_img), cv.COLOR_RGB2BGR)
    # now finally extract out the rectangle from the scan image
    extracted_rect_img = cv.warpPerspective(
        opencv_img, M_s_to_r, (rect_width_int, rect_height_int)
    )
    # convert the result to a PIL.Image
    resulting_img = Image.fromarray(cv.cvtColor(extracted_rect_img, cv.COLOR_BGR2RGB))

    with BytesIO() as fh:
        resulting_img.save(fh, format="png")
        return fh.getvalue()


class RectangleExtractor:
    """Provides operations on scanned images based on a reference image.

    Instances are particular to a page/version reference image.  They
    stores information and cached calculations about a coordinate system
    in the QR-code locations, enabling information to be looked up in a
    scanned image based on locations chosen from the reference image.

    If you construct a RectangleExtractor for version 1 and use it on
    version 2, you are playing with fire a bit (b/c maybe version 1 is
    on A4 paper but version 2 is on Letter paper).  More likely, perhaps
    the boxes you're looking to get are not in *precisely* the same place.
    If you really want to do this, look for underscore kwargs like
    `_version_ignore`.  This is unsupported.
    """

    def __init__(self, version: int, page: int) -> None:
        self.page_number = page
        self.version = version

        try:
            rimg_obj = ReferenceImage.objects.get(version=version, page_number=page)
            self.rimg_obj = rimg_obj
        except ReferenceImage.DoesNotExist:
            raise ValueError(f"There is no reference image for v{version} pg{page}.")

        r = get_reference_rectangle_from_QR_data(rimg_obj.parsed_qr)
        # rectangle described by location of the 3 qr-code stamp centres of the reference image
        self.LEFT = r["left"]
        self.RIGHT = r["right"]
        self.TOP = r["top"]
        self.BOTTOM = r["bottom"]
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
        return _get_affine_transf_matrix_ref_to_QR_target(
            (self.LEFT, self.TOP, self.RIGHT, self.BOTTOM), qr_dict
        )

    def extract_rect_region(
        self,
        paper_number: int,
        left_f: float,
        top_f: float,
        right_f: float,
        bottom_f: float,
        *,
        _version_ignore: bool = False,
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

        Keyword Args:
            _version_ignore: RectangleExtractor is designed to be specific
                to a version provided at time of construction.  If you like
                living somewhat dangerously (and/or have knowledge that your
                version layouts are identical), then you can bypass this...
                TODO: note underscore: used for internal hackery, may not last.

        Returns:
            The bytes of the image in png format, or none if errors.

        Raises:
            ObjectDoesNotExist: if that paper number does not have our page
                and our version.
        """
        # start by getting the scanned image
        paper_obj = Paper.objects.get(paper_number=paper_number)
        if _version_ignore:
            print("recklessly ignoring the version...")
            img_obj = (
                FixedPage.objects.select_related("image", "image__baseimage")
                .filter(page_number=self.page_number, paper=paper_obj)[0]
                .image
            )
        else:
            img_obj = (
                FixedPage.objects.select_related("image", "image__baseimage")
                .filter(
                    version=self.version, page_number=self.page_number, paper=paper_obj
                )[0]
                .image
            )

        # TODO: Issue #3888 this `.path` assumes storage is local and will fail
        # with a NotImplementedError when FileField uses remote storage.
        return extract_rect_region_from_image(
            img_obj.baseimage.image_file.path,
            img_obj.parsed_qr,
            left_f,
            top_f,
            right_f,
            bottom_f,
            (self.LEFT, self.TOP, self.RIGHT, self.BOTTOM),
            pre_rotation=img_obj.rotation,
        )

    def build_zipfile(
        self,
        dest_filename: str | Path,
        left_f: float,
        top_f: float,
        right_f: float,
        bottom_f: float,
    ) -> None:
        """Construct a zipfile of the extracted rectangular regions and save in dest_filename.

        Warning: This constructs the pngs for each extracted region in
        memory, but then saves the resulting (potentially very large)
        zipfile on disc. This could cause problems if large rectangles
        are selected from many pages.
        """
        # paper_numbers may be duplicated if there are multiple quesetions on a page
        paper_numbers = set(
            PaperInfoService.get_paper_numbers_containing_page(
                self.page_number, version=self.version, scanned=True
            )
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

            # DEBUG BRYAN (TEMP)
            # need reference
            if self.rimg_obj.parsed_qr is not None:
                dat = extract_rect_region_from_image(
                    Path(self.rimg_obj.image_file.path),
                    self.rimg_obj.parsed_qr,
                    left_f,
                    top_f,
                    right_f,
                    bottom_f,
                    (self.LEFT, self.TOP, self.RIGHT, self.BOTTOM),
                )
                if dat:
                    archive.writestr("ref.png", dat)

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

        Raises:
            ValueError: missing or incomplete reference images.
        """
        try:
            rimg_obj = ReferenceImage.objects.get(
                version=self.version, page_number=self.page_number
            )
        except ReferenceImage.DoesNotExist as e:
            raise ValueError(
                f"There is no reference image for v{self.version} pg{self.page_number}."
            ) from e
        # ref-image into cv image: cannot just use imread b/c of DB abstraction
        img_bytes = rimg_obj.image_file.read()
        return get_largest_rectangle_contour_from_image(
            img_bytes,
            (self.FULL_WIDTH, self.FULL_HEIGHT),
            (self.LEFT, self.TOP, self.RIGHT, self.BOTTOM),
            region=region,
        )

    def get_cropped_ref_img(self, rects: dict[str, float]) -> np.ndarray:
        """Get numpy array of cropped reference image.

        Args:
            rects: a dictionary defining the cropped region. Must have these keys:
            [left, top, right, bottom]

        Returns:
            A numpy array of the cropped reference image.
        """
        expected_keys = {"left", "top", "right", "bottom"}
        if not expected_keys.issubset(rects):
            missing = expected_keys - rects.keys()
            raise KeyError(f"Missing rect keys: {missing}")

        left, top, right, bottom = (
            rects["left"],
            rects["top"],
            rects["right"],
            rects["bottom"],
        )
        if self.rimg_obj.parsed_qr is None:
            raise ValueError("Reference image does not have parsed_qr data.")

        cropped_ref_bytes = extract_rect_region_from_image(
            Path(self.rimg_obj.image_file.path),
            self.rimg_obj.parsed_qr,
            left,
            top,
            right,
            bottom,
            (self.LEFT, self.TOP, self.RIGHT, self.BOTTOM),
        )

        if cropped_ref_bytes is None:
            raise ValueError("Failed to extract rectangle region from reference image.")

        # Convert bytes to NumPy array
        with BytesIO(cropped_ref_bytes) as fh:
            pil_img = Image.open(fh)
            cropped_ref = np.array(pil_img)

        return cropped_ref

    def get_cropped_scanned_img(
        self, paper_num: int, rects: dict[str, float]
    ) -> np.ndarray:
        """Get numpy array of a cropped scanned image.

        Args:
            paper_num: the paper number whose scanned page will be extracted
            rects: a dictionary defining the cropped region. Must have these keys:
                [left, top, right, bottom].

        Returns:
            A numpy array of the cropped scanned image.
        """
        expected_keys = {"left", "top", "right", "bottom"}
        if not expected_keys.issubset(rects):
            missing = expected_keys - rects.keys()
            raise KeyError(f"Missing rect keys: {missing}")

        left, top, right, bottom = (
            rects["left"],
            rects["top"],
            rects["right"],
            rects["bottom"],
        )

        cropped_scanned_bytes = self.extract_rect_region(
            paper_num, left, top, right, bottom
        )

        if cropped_scanned_bytes is None:
            raise ValueError("Failed to extract rectangle region from scanned image.")

        with BytesIO(cropped_scanned_bytes) as fh:
            pil_img = Image.open(fh)
            cropped_scanned = np.array(pil_img)

        return cropped_scanned


def get_largest_rectangle_contour_from_image(
    img_bytes: bytes,
    img_size: tuple[int, int],
    reference_region: tuple[int | float, int | float, int | float, int | float],
    *,
    region: None | dict[str, float] = None,
) -> None | dict[str, float]:
    """Implementation of find rectangle, for testing."""
    IMG_WIDTH, IMG_HEIGHT = img_size
    LEFT, TOP, RIGHT, BOTTOM = reference_region
    WIDTH = RIGHT - LEFT
    HEIGHT = BOTTOM - TOP

    raw_bytes_as_1d_array: Any = np.frombuffer(img_bytes, np.uint8)
    src_image = cv.imdecode(raw_bytes_as_1d_array, cv.IMREAD_COLOR)
    if src_image is None:
        raise ValueError("Could not read reference image")
    # if a region is specified then cut it out from the original image,
    # but we need to remember to map the resulting rectangle back to the
    # original coordinate system.
    # make sure region is padded by a few pixels.
    pad = 16
    if region:
        # convert [0, 1] coordinates into pixels
        img_left = floor(region["left_f"] * WIDTH + LEFT) - pad
        img_right = ceil(region["right_f"] * WIDTH + LEFT) + pad
        img_top = floor(region["top_f"] * HEIGHT + TOP) - pad
        img_bottom = ceil(region["bottom_f"] * HEIGHT + TOP) + pad
        # cap pixel values in the image domain
        img_left = max(img_left, 0)
        img_right = min(img_right, IMG_WIDTH)
        img_top = max(img_top, 0)
        img_bottom = min(img_bottom, IMG_HEIGHT)
        # crop the image
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
    contours = cv.findContours(edged_image, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
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
    if box_contour is None:
        return None
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
    left_f = (left - LEFT) / WIDTH
    right_f = (right - LEFT) / WIDTH
    top_f = (top - TOP) / HEIGHT
    bottom_f = (bottom - TOP) / HEIGHT

    # cast each to float (from numpy.float64)
    return {
        "left_f": float(left_f),
        "top_f": float(top_f),
        "right_f": float(right_f),
        "bottom_f": float(bottom_f),
    }
