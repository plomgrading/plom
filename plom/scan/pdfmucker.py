# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Aden Chan

"""Command Line Tool to simulate PDF errors while scanning"""

from typing import List
import argparse
import fitz  # PyMuPDF
import random
from PIL import Image, ImageEnhance
import io
import cv2
import math
import numpy as np
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Web_Plom.settings")

def get_parser() -> argparse.ArgumentParser:
    """Returns the argument parser used to parse command line input

    Returns:
        argparse.ArgumentParser: ArgumentParser used to parse input
    """
    parser = argparse.ArgumentParser(
        prog="pdf-mucker", description="Simulate PDF Scanning Errors"
    )

    parser.add_argument("filename", type=str, help='File to be "mucked"')
    parser.add_argument("page", type=int, help="Page number to muck")
    parser.add_argument(
        "operation",
        choices=[
            "tear",
            "fold",
            "rotate",
            "compress",
            "jam",
            "hide",
            "corrupt",
            "stretch",
            "lighten",
            "darken",
        ],
        help="Type of operation to perform",
    )
    parser.add_argument(
        "corner",
        nargs="?",
        choices=["top_left", "top_right", "bottom_left", "bottom_right"],
        help="Corner to target for tear, fold, hide, or cover",
    )
    parser.add_argument(
        "--severity",
        type=float,
        default=0.5,
        help="Severity of the operation (0.0 to 1.0, default 0.5)",
    )
    parser.add_argument(
        "--jaggedness", type=int, default=2, help="Jaggedness of the tear"
    )

    return parser


def validate_args(args):
    """Ensure that corner is provided for operation in [tear, fold, hide, cover]

    Raises:
        ValueError: if the operation is set, but corner is not provided
    """
    if args.operation in ["tear", "fold", "hide", "cover"] and args.corner is None:
        raise ValueError(f"The corner argument is required for {args.operation}")


def get_page(file: fitz.Document, page_number: int) -> fitz.Page:
    """Get a page from the document

    Args:
        file (fitz.Document): The PDF document
        page_number (int): The page number to get (1-based)

    Returns:
        fitz.Page: The specified page

    Raises:
        ValueError: If the page number is out of range
    """
    if page_number < 1 or page_number > file.page_count:
        raise ValueError(
            f"Invalid page number {page_number}. "
            f"Must be between 1 and {file.page_count}."
        )

    return file.load_page(page_number - 1)


def generate_tear_points(
    corner: str, severity: float, x_max: float, y_max: float, jaggedness: int
) -> List[fitz.Point]:
    """Generates points for a tear with jagged edges

    Args:
        corner (str): Specify which corner to tear. Valid options are:
            'top_left', 'top_right', 'bottom_left', 'bottom_right'
        severity (float): How severe the tear should be, as a percentage.
        Must be between (0, 1.0)
        x_max (float): Maximum x value for the page
        y_max (float): Maximum y value for the page

    Returns:
        List[fitz.Point]: List of points used for the tear
    """
    if severity < 0.1:
        severity = 0.1

    points = []

    if corner == "top_left":
        points.append(fitz.Point(0, 0))
        for i in range(1, 11):
            points.append(
                fitz.Point(
                    random.uniform(0, severity) * x_max,
                    random.uniform(-jaggedness, jaggedness),
                )
            )
        for i in range(1, 11):
            points.append(
                fitz.Point(
                    random.uniform(-jaggedness, jaggedness),
                    random.uniform(0, severity) * y_max,
                )
            )
    elif corner == "top_right":
        points.append(fitz.Point(x_max, 0))
        for i in range(1, 11):
            points.append(
                fitz.Point(
                    x_max - random.uniform(0, severity) * x_max,
                    random.uniform(-jaggedness, jaggedness),
                )
            )
        for i in range(1, 11):
            points.append(
                fitz.Point(
                    x_max + random.uniform(-jaggedness, jaggedness),
                    random.uniform(0, severity) * y_max,
                )
            )
    elif corner == "bottom_left":
        points.append(fitz.Point(0, y_max))
        for i in range(1, 11):
            points.append(
                fitz.Point(
                    random.uniform(0, severity) * x_max,
                    y_max + random.uniform(-jaggedness, jaggedness),
                )
            )
        for i in range(1, 11):
            points.append(
                fitz.Point(
                    random.uniform(-jaggedness, jaggedness),
                    y_max - random.uniform(0, severity) * y_max,
                )
            )
    elif corner == "bottom_right":
        points.append(fitz.Point(x_max, y_max))
        for i in range(1, 11):
            points.append(
                fitz.Point(
                    x_max - random.uniform(0, severity) * x_max,
                    y_max + random.uniform(-jaggedness, jaggedness),
                )
            )
        for i in range(1, 11):
            points.append(
                fitz.Point(
                    x_max + random.uniform(-jaggedness, jaggedness),
                    y_max - random.uniform(0, severity) * y_max,
                )
            )

    return points


def mirror_points(points: List[fitz.Point], x_max: float) -> List[fitz.Point]:
    """Mirrors points horizontally across the middle of the page

    Args:
        points (List[fitz.Point]): List of points to mirror
        x_max (float): Maximum x value for the page

    Returns:
        List[fitz.Point]: List of mirrored points
    """
    return [fitz.Point(x_max - point.x, point.y) for point in points]


def tear_double_sided(
    pages: List[fitz.Page], corner: str, severity: float, jaggedness: int
):
    """Tears both sides of a single PDF page

    Args:
        pages (List[fitz.Page]): PDF pages to alter
        corner (str): Specify which corner to tear. Valid options are:
            'top_left', 'top_right', 'bottom_left', 'bottom_right'
        severity (float): How severe the tear should be, as a percentage.
        Must be between (0, 1.0)
    """
    x_max = pages[0].rect.width
    y_max = pages[0].rect.height
    color = (0, 0, 0)  # Black color for the tear

    # Generate tear points for the front side
    points = generate_tear_points(corner, severity, x_max, y_max, jaggedness)
    pages[0].draw_polyline(points, color=color, width=3, fill=color)

    if len(pages) > 1:
        # Generate mirrored points for the back side
        mirrored = mirror_points(points, x_max)
        pages[1].draw_polyline(mirrored, color=color, width=3, fill=color)


def generate_fold_points(corner: str, severity: float, r: fitz.Rect):
    """Generates points for a fold
    Args:
    corner (str): Specify which corner to fold. Valid options are:
    'top_left', 'top_right', 'bottom_left', 'bottom_right'
    severity (float): How severe the fold should be, as a percentage.
    Must be between (0, 1.0)
    rect(Rectangle)
    r (fitz.Rect): the rectangle representation of the page's dimension

    Returns:
    List[fitz.Point]: List of points used for the fold.
    Invariant: item at index 0 is the corner, and
    item at index 3 is the innermost vertex of an inward fold
    """
    side = severity * 0.5 * r.width
    if corner == "top_left":
        vertex1 = r.tl
        vertex2 = fitz.Point(r.tl.x + side, r.tl.y)
        vertex3 = fitz.Point(r.tl.x, r.tr.y + side)
        vertex4 = fitz.Point(r.tl.x + side, r.tl.y + side)

    elif corner == "top_right":
        vertex1 = r.tr
        vertex2 = fitz.Point(r.tr.x - side, r.tr.y)
        vertex3 = fitz.Point(r.tr.x, r.tr.y + side)
        vertex4 = fitz.Point(r.tr.x - side, r.tr.y + side)

    elif corner == "bottom_left":
        vertex1 = r.bl
        vertex2 = fitz.Point(r.bl.x + side, r.bl.y)
        vertex3 = fitz.Point(r.bl.x, r.bl.y - side)
        vertex4 = fitz.Point(r.bl.x + side, r.bl.y - side)

    elif corner == "bottom_right":
        vertex1 = r.br
        vertex2 = fitz.Point(r.br.x - side, r.br.y)
        vertex3 = fitz.Point(r.br.x, r.br.y - side)
        vertex4 = fitz.Point(r.br.x - side, r.br.y - side)

    return [vertex1, vertex2, vertex3, vertex4]


def get_corner_pixmap(
    page: fitz.Page, corner: str, severity: float, r: fitz.Rect
) -> fitz.Pixmap:
    """Gets the pixmap of a corner

    Args:
        page (fitz.Page): Page to get pixmap from
        corner (str): Corner to get pixmap from
        severity (float): Severity of the fold
        r (fitz.Rect): The rectangle representation of `page`'s dimension

    Returns:
        fitz.Pixmap: Pixmap of the folded area
    """
    mat = fitz.Matrix(2, 2)
    return page.get_pixmap(matrix=mat, clip=get_bounding_box(corner, severity, r))


def get_bounding_box(corner: str, severity: float, r: fitz.Rect) -> fitz.Rect:
    """Get the bounding box of a fold

    Args:
        corner (str): Corner of the fold
        severity (float): Severity of the bold
        r (fitz.Rect): Rectangle representation of the page being folded

    Returns:
        fitz.Rect: Bounding box of the fold
    """
    side = severity * 0.5 * r.width
    if corner == "top_left":
        clip = fitz.Rect(r.tl, fitz.Point(r.tl.x + side, r.tl.y + side))
    elif corner == "top_right":
        clip = fitz.Rect(
            fitz.Point(r.tr.x - side, r.tr.y), fitz.Point(r.tr.x, r.tr.y + side)
        )
    elif corner == "bottom_left":
        clip = fitz.Rect(
            fitz.Point(r.bl.x, r.bl.y - side), fitz.Point(r.bl.x + side, r.bl.y)
        )
    elif corner == "bottom_right":
        clip = fitz.Rect(fitz.Point(r.br.x - side, r.bl.y - side), r.br)

    return clip


def fold_page(pages: List[fitz.Page], corner: str, severity: float):
    """Fold both sides of a single PDF page
    Assumption:
    1. the page number given in the argument
    is assumed to be the page that is folded inward
    2. The fold is an isosceles triangle

    Args:
        pages (List[fitz.Page]): PDF pages to alter
        corner (str): Specify which corner to fold. Valid options are:
             'top_left', 'top_right', 'bottom_left', 'bottom_right'
        severity (float): How severe fold tear should be, as a percentage.
             Must be between (0, 1.0)
        A quarter page folded is considered as most severe fold
    """
    r = pages[0].rect
    points = generate_fold_points(corner, severity, r)
    # color
    edge_out = (0.2, 0.2, 0.2)
    edge_in = (0.7, 0.7, 0.7)
    out_clr = (0, 0, 0)

    bounding_box = get_bounding_box(corner, severity, r)
    pixmap = get_corner_pixmap(pages[1], corner, severity, r)
    pages[0].insert_image(bounding_box, pixmap=pixmap, rotate=180)

    pages[0].draw_quad(bounding_box.quad, color=edge_in, width=1)
    pages[0].draw_polyline(points[:-1], color=edge_out, width=1, fill=out_clr)

    if len(pages) > 1:
        # Generate mirrored points for the back side
        mirrored = mirror_points(points, r.width)
        pages[1].draw_polyline(mirrored[:-1], color=edge_out, width=1, fill=out_clr)


def rotate_page(doc: fitz.Document, page_number: int, severity: float):
    """Rotate a page counter clockwise

    Args:
        doc(fitz.Document): the document whose page will be rotated
        page_number(int): the page_number of the document
        to be rotated (0 indexed)
        severity(float): the severity represents the
        linear mapping of counter clockwise rotation,
        where [0,1] mapped to [0, 180] degrees of counter clockwise rotation
    """
    rotate_degree = severity * 180

    src = fitz.open()
    src.insert_pdf(doc)

    doc.delete_page(page_number)
    page = doc.new_page(pno=page_number)
    page.show_pdf_page(page.rect, src, pno=page_number, rotate=rotate_degree)


def compress(doc: fitz.Document, page_num, severity: float):
    """Compress an image, such that the quality of a page in the pdf is worsen

    Args:
    doc(fitz.Document): the document whose page will be compressed
    page_num(int): the page number of the document to be compressed (0 indexed)
    severity(float): The severity is linearly mapped, where [0,1] of severity
    is mapped to [100, 0] jpg_quality
    """
    jpg_quality = 100 - int(severity * 100)
    page = doc[page_num]

    # convert the page to PIL Image
    temp_pix = page.get_pixmap()
    image = Image.frombytes("RGB", [temp_pix.width, temp_pix.height], temp_pix.samples)

    # Intermediate saving step to change the jpg quality (saved to buffer)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=jpg_quality)

    # Retrieve the buffer and insert that image to the original document
    image_data = buffer.getvalue()
    pix = fitz.Pixmap(image_data)
    doc[page_num].insert_image(page.rect, pixmap=pix)


def lighten(doc: fitz.Document, page_num, severity: float):
    """Lighten an image, increasing it's average brightness

    Args:
    doc(fitz.Document): the target document
    page_num(int): the target page number (0 indexed)
    severity(float): how much lighter the image gets
    """
    page = doc[page_num]

    # Preserve quality of page
    matrix = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=matrix)
    pix.gamma_with(0.5 - severity * 0.5)
    page.insert_image(page.rect, pixmap=pix)


def darken(doc: fitz.Document, page_num, severity: float):
    """Darken an image, decreasing it's average brightness

    Args:
    doc(fitz.Document): the target document
    page_num(int): the target page number (0 indexed)
    severity(float): how much lighter the image gets
    """
    page = doc[page_num]

    # Preserve quality of page
    matrix = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=matrix)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1 - severity)

    bytestream = io.BytesIO()
    img.save(bytestream, "JPEG")
    page.insert_image(page.rect, stream=bytestream)


def jam(doc: fitz.Document, page_num, severity: float):
    """Simulates a page feed error, where a row is smeared downwards.

    Args:
    doc(fitz.Document): the target document
    page_num(int): the target page number
    severity(float): The severity of the smear, which is how far up the
        page it starts
    """
    page = doc[page_num]

    # convert the page to PIL Image
    temp_pix = page.get_pixmap()
    image = Image.frombytes("RGB", [temp_pix.width, temp_pix.height], temp_pix.samples)

    start_row = image.height - int(image.height * severity)
    cropbox = (0, start_row, image.width, start_row + 1)
    row_img = image.crop(cropbox)
    row_img = row_img.resize((image.width, image.height - start_row + 1))
    image.paste(row_img, (0, start_row - 1, image.width, image.height))

    bytestream = io.BytesIO()
    image.save(bytestream, "JPEG")
    page.insert_image(page.rect, stream=bytestream)


def stretch(page: fitz.Page, severity: float):
    """Stretch a page, expanding near the top and compressing near the bottom.

    The stretch works through non-linear shifting for the pixel in the
    y-direction (particularly shifting each pixel downward).

    This implementation uses the sine function
    (with period of 2 * height), so that the shift's sign is constant throughout
    the operation (negative in this case). Additionally, using half sine wave
    as the shifter causes an increasing shifting magnitude from 0 to h/2 and a
    decreasing shifting magnitude from h/2 onward. The effect is caused by the
    increasing - decreasing magnitude of the y-shifts. Basically everything tends
    to be stretched down (a pixel will be replaced by its upper peers, because of
    negative shift), so when the shifting magnitude is increasing and around its peak,
    the majority of the page will have been stretched down, leaving a small portion on
    the bottom (where the shifting magnitude is decreasing and is already small), and
    effectively creates a compression effect.

    Args:
        page: the page to be stretched.
        severity: the severity of the stretch.
    """
    amplitude = 200 * severity
    pix = page.get_pixmap()
    pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    height, width, _ = img.shape

    img_output = np.zeros(img.shape)
    for x in range(width):
        for y in range(height):
            # *Period is set to 2* height, such that delta_y's sign is constant
            # *The default sign is negative, such that the top page is
            # stretched and the bottom page is squashed.
            delta_y = -int(amplitude * math.sin(2 * math.pi * y / (2 * height)))
            if (y + delta_y) < height and (y + delta_y) >= 0:
                img_output[y, x] = img[(y + delta_y), x]

    cv2.imwrite("output.png", img_output)


def detect_qr_code_area(corner: str, page: fitz.Page) -> fitz.Rect:
    """Detects a single QR code area based on the specified corner

    Args:
        corner (str): The corner to target
        page (fitz.Page): The PDF page to analyze

    Returns:
        fitz.Rect: The detected QR code area
    """
    page_width = page.rect.width
    page_height = page.rect.height

    if corner == "top_left":
        qr_area = fitz.Rect(15, 15, 100, 100)
    elif corner == "top_right":
        qr_area = fitz.Rect(page_width - 100, 15, page_width - 15, 100)
    elif corner == "bottom_left":
        qr_area = fitz.Rect(15, page_height - 100, 100, page_height - 15)
    elif corner == "bottom_right":
        qr_area = fitz.Rect(
            page_width - 100, page_height - 100, page_width - 15, page_height - 15
        )

    return qr_area


def qr_hide(page: fitz.Page, qr_area: fitz.Rect):
    """Covers an area of the page where a QR code might be located

    Args:
        page (fitz.Page): The PDF page to alter
        qr_area (fitz.Rect): Rectangle area to cover
    """
    page.draw_rect(qr_area, color=(0, 0, 0), fill=(0, 0, 0))


def qr_corrupt(page: fitz.Page, qr_area: fitz.Rect):
    """Corrupts an area of the page where a QR code might be located

    Args:
        page (fitz.Page): The PDF page to alter
        qr_area (fitz.Rect): Rectangle area to corrupt
    """
    num_lines = 10
    for _ in range(num_lines):
        x1 = random.uniform(qr_area.x0, qr_area.x1)
        y1 = random.uniform(qr_area.y0, qr_area.y1)
        x2 = random.uniform(qr_area.x0, qr_area.x1)
        y2 = random.uniform(qr_area.y0, qr_area.y1)
        page.draw_line(fitz.Point(x1, y1), fitz.Point(x2, y2), color=(0, 0, 0), width=2)


def main():
    parser = get_parser()
    args = parser.parse_args()
    validate_args(args)

    # Open file
    file = fitz.open(args.filename)

    # Manipulate file
    page_number = args.page
    pages = [get_page(file, page_number)]
    if page_number % 2 == 0:
        other_page = page_number - 1
    else:
        other_page = page_number + 1

    if other_page <= file.page_count and other_page > 0:
        pages.append(get_page(file, other_page))

    # Perform the selected operation
    if args.operation == "tear":
        tear_double_sided(pages, args.corner, args.severity, args.jaggedness)
    elif args.operation == "fold":
        if len(pages) < 2:
            raise ValueError("Invalid page specified for fold operation")
        fold_page(pages, args.corner, args.severity)
    elif args.operation == "rotate":
        rotate_page(file, page_number - 1, args.severity)
    elif args.operation == "compress":
        compress(file, page_number - 1, args.severity)
    elif args.operation == "lighten":
        lighten(file, page_number - 1, args.severity)
    elif args.operation == "darken":
        darken(file, page_number - 1, args.severity)
    elif args.operation == "jam":
        jam(file, page_number - 1, args.severity)
    elif args.operation == "stretch":
        stretch(pages[0], args.severity)
    elif args.operation == "hide":
        qr_area = detect_qr_code_area(args.corner, pages[0])
        qr_hide(pages[0], qr_area)
    elif args.operation == "corrupt":
        qr_area = detect_qr_code_area(args.corner, pages[0])
        qr_corrupt(pages[0], qr_area)
    else:
        raise RuntimeError("Invalid operation specified")

    # Save file (stretch operation is saved as png and is saved
    # in the function call)
    # if args.operation != "stretch":
        # file.save(args.filename, incremental=True)
    file.saveIncr()

if __name__ == "__main__":
    main()
