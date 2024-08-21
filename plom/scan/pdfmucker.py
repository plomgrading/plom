# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Colin B. Macdonald

"""Command Line Tool to simulate PDF errors while scanning."""

from __future__ import annotations

import io
import math
import random
import tempfile

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageEnhance


class PDFMuckerService:

    def get_page(self, file: fitz.Document, page_number: int) -> fitz.Page:
        """Get a page from the document.

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

    def generate_dummy_pdf(self) -> str:
        # Create a temporary file with a .pdf suffix
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
            # Create a new PDF document
            dummy_pdf = fitz.open()

            # Add a page to the PDF with A4 dimensions
            dummy_page = dummy_pdf.new_page(width=595, height=842)

            # Define the text to be added
            text = "Just for testing purpose"

            # Define text position and font size
            text_position = (50, 100)  # (x, y) in points from top-left
            font_size = 20

            # Add text to the page
            dummy_page.insert_text(text_position, text, fontsize=font_size)

            # Save the PDF to the temporary file
            dummy_pdf.save(temp_pdf.name)

            # Close the PDF document
            dummy_pdf.close()

            # Return the path to the temporary file
            return temp_pdf.name

    def add_operation_description(
        self,
        page: fitz.Page,
        operation: str,
        *,
        corner: str | None = None,
    ) -> None:
        """Adds a text description of the operation to the page."""
        operation_description = {
            "tear": "Simulated page damage: torn corner.",
            "fold": "Simulated page damage: folded corner.",
            "rotate": "Simulated page damage: rotated page.",
            "compress": "Simulated page damage: compressed image quality.",
            "lighten": "Simulated page damage: lightened image.",
            "darken": "Simulated page damage: darkened image.",
            "jam": "Simulated page damage: page jammed in scanner.",
            "stretch": "Simulated page damage: stretched page.",
            "hide": "Simulated page damage: QR code hidden.",
            "corrupt": "Simulated page damage: QR code corrupted.",
        }
        text = operation_description.get(operation, "Simulated page damage.")

        # Default position at the top of the page
        position = (100, 20)

        # If operation affects the top of the page, move text to the bottom, to avoid covering the text
        if corner in ["top_left", "top_right"]:
            position = (100, page.rect.height - 20)

        page.insert_text(
            position,  # Position determined by operation and corner
            text,
            fontsize=14,
            color=(0, 0, 0.8),
        )

    def generate_tear_points(
        self, corner: str, severity: float, x_max: float, y_max: float, jaggedness: int
    ) -> list[fitz.Point]:
        """Generates points for a tear with jagged edges.

        Args:
            corner: Specify which corner to tear. Valid options are:
                'top_left', 'top_right', 'bottom_left', 'bottom_right'
            severity: How severe the tear should be, as a percentage.
            Must be between (0, 1.0)
            x_max: Maximum x value for the page
            y_max (): Maximum y value for the page
            jaggedness: Controls how jagged the tear should be

        Returns:
            List of points used for the tear.
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

    def mirror_points(self, points: list[fitz.Point], x_max: float) -> list[fitz.Point]:
        """Mirrors points horizontally across the middle of the page.

        Args:
            points: List of points to mirror
            x_max: Maximum x value for the page

        Returns:
            List of mirrored points
        """
        return [fitz.Point(x_max - point.x, point.y) for point in points]

    def tear_double_sided(
        self, pages: list[fitz.Page], corner: str, severity: float, jaggedness: int
    ):
        """Tears both sides of a single PDF page.

        Args:
            pages: PDF pages to alter.
            corner: Specify which corner to tear. Valid options are:
                'top_left', 'top_right', 'bottom_left', 'bottom_right'.
            severity: How severe the tear should be, as a percentage.
                 Must be between (0, 1.0).
            jaggedness: Controls how jagged the tear should be.
        """
        x_max = pages[0].rect.width
        y_max = pages[0].rect.height
        color = (0, 0, 0)  # Black color for the tear

        # Generate tear points for the front side
        points = self.generate_tear_points(corner, severity, x_max, y_max, jaggedness)
        pages[0].draw_polyline(points, color=color, width=3, fill=color)

        if len(pages) > 1:
            # Generate mirrored points for the back side
            mirrored = self.mirror_points(points, x_max)
            pages[1].draw_polyline(mirrored, color=color, width=3, fill=color)

    def generate_fold_points(self, corner: str, severity: float, r: fitz.Rect):
        """Generates points for a fold.

        Args:
            corner (str): Specify which corner to fold. Valid options are:
                'top_left', 'top_right', 'bottom_left', 'bottom_right'.
            severity (float): How severe the fold should be, as a percentage.
                Must be between (0, 1.0).
            r (fitz.Rect): The rectangle representation of the page's dimension.

        Returns:
            List of points used for the fold.
            Invariant: item at index 0 is the corner, and
            item at index 3 is the innermost vertex of an inward fold.
        """
        side = severity * 0.5 * r.width
        vertex1, vertex2, vertex3, vertex4 = (
            None,
            None,
            None,
            None,
        )  # Initialize variables

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
        self, page: fitz.Page, corner: str, severity: float, r: fitz.Rect
    ) -> fitz.Pixmap:
        """Gets the pixmap of a corner.

        Args:
            page (fitz.Page): Page to get pixmap from.
            corner (str): Corner to get pixmap from.
            severity (float): Severity of the fold.
            r (fitz.Rect): The rectangle representation of `page`'s dimension.

        Returns:
            fitz.Pixmap: Pixmap of the folded area.
        """
        mat = fitz.Matrix(2, 2)
        return page.get_pixmap(
            matrix=mat, clip=self.get_bounding_box(corner, severity, r)
        )

    def get_bounding_box(self, corner: str, severity: float, r: fitz.Rect) -> fitz.Rect:
        """Get the bounding box of a fold.

        Args:
            corner (str): Corner of the fold.
            severity (float): Severity of the bold.
            r (fitz.Rect): Rectangle representation of the page being folded.

        Returns:
            fitz.Rect: Bounding box of the fold.
        """
        side = severity * 0.5 * r.width
        clip = None

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

    def fold_page(self, pages: list[fitz.Page], corner: str, severity: float) -> None:
        """Fold both sides of a single PDF page.

        Assumption:
            1. The page number given in the argument is assumed to be the page that is folded inward.
            2. The fold is an isosceles triangle.

        Args:
            pages: PDF pages to alter.
            corner (str): Specify which corner to fold. Valid options are:
                'top_left', 'top_right', 'bottom_left', 'bottom_right'.
            severity (float): How severe fold tear should be, as a percentage.
                Must be between (0, 1.0).
            A quarter page folded is considered as most severe fold.
        """
        r = pages[0].rect
        points = self.generate_fold_points(corner, severity, r)
        # color
        edge_out = (0.2, 0.2, 0.2)
        edge_in = (0.7, 0.7, 0.7)
        out_clr = (0, 0, 0)

        bounding_box = self.get_bounding_box(corner, severity, r)
        pixmap = self.get_corner_pixmap(pages[1], corner, severity, r)
        pages[0].insert_image(bounding_box, pixmap=pixmap, rotate=180)

        pages[0].draw_quad(bounding_box.quad, color=edge_in, width=1)
        pages[0].draw_polyline(points[:-1], color=edge_out, width=1, fill=out_clr)

        if len(pages) > 1:
            # Generate mirrored points for the back side
            mirrored = self.mirror_points(points, r.width)
            pages[1].draw_polyline(mirrored[:-1], color=edge_out, width=1, fill=out_clr)

    def obscure_qr_codes_in_paper(self, pdf_doc: fitz.Document) -> None:
        """Hide qr-codes for demo purposes.

        On last page paint squares at bottom of page to hide 2
        qr-codes, and on second-last page, paint squares at the
        top of the page to hide 1 qr-code.

        Args:
            pdf_doc (fitz.Document): a pdf document of a test-paper.

        Returns:
            None, but modifies ``pdf_doc``  as a side effect.
        """
        # magic numbers for obscuring the qr-codes
        left = 15
        right = 90
        page = pdf_doc[-1]
        # grab the bounding box of the page to get its height/width
        bnd = page.bound()
        page.draw_rect(
            fitz.Rect(left, bnd.height - right, right, bnd.height - left),
            color=(0, 0, 0),
            fill=(0.2, 0.2, 0.75),
            radius=0.05,
        )
        page.draw_rect(
            fitz.Rect(
                bnd.width - right,
                bnd.height - right,
                bnd.width - left,
                bnd.height - left,
            ),
            color=(0, 0, 0),
            fill=(0.2, 0.2, 0.75),
            radius=0.05,
        )
        tw = fitz.TextWriter(bnd)
        tw.append(
            fitz.Point(100, bnd.height - 20),
            "Simulated page damage: unreadable bottom QR codes",
            fontsize=14,
        )
        tw.write_text(page, color=(0, 0, 0.8))

        page = pdf_doc[-2]
        bnd = page.bound()
        page.draw_rect(
            fitz.Rect(
                bnd.width - right,
                left,
                bnd.width - left,
                right,
            ),
            color=(0, 0, 0),
            fill=(0.2, 0.2, 0.75),
            radius=0.05,
        )
        page.draw_rect(
            fitz.Rect(
                left,
                left,
                right,
                right,
            ),
            color=(0, 0, 0),
            fill=(0.2, 0.2, 0.75),
            radius=0.05,
        )
        tw = fitz.TextWriter(bnd)
        tw.append(
            fitz.Point(100, 15),
            "Simulated page damage: unreadable top QR code",
            fontsize=14,
        )
        tw.write_text(page, color=(0, 0, 0.8))

    def rotate_page(self, doc: fitz.Document, page_number: int, severity: float):
        """Rotate a page counterclockwise.

        Args:
            doc (fitz.Document): The document whose page will be rotated.
            page_number(int): The page number of the document to be rotated (0 indexed).
            severity(float): The severity represents the linear mapping of counterclockwise rotation,
                            where [0,1] is mapped to [0, 180] degrees of counterclockwise rotation.
        """
        rotate_degree = severity * 180

        src = fitz.open()
        src.insert_pdf(doc)

        doc.delete_page(page_number)
        page: fitz.Page = doc.new_page(pno=page_number)
        page.show_pdf_page(page.rect, src, pno=page_number, rotate=rotate_degree)
        self.add_operation_description(page, "rotate", corner=None)

    def compress(self, doc: fitz.Document, page_num, severity: float):
        """Compress an image, such that the quality of a page in the pdf is worsened.

        Args:
            doc (fitz.Document): The document whose page will be compressed.
            page_num(int): The page number of the document to be compressed (0 indexed).
            severity(float): The severity is linearly mapped, where [0,1] of severity is mapped to [100, 0] jpg_quality.
        """
        jpg_quality = 100 - int(severity * 100)
        page = doc[page_num]

        # Convert the page to PIL Image
        temp_pix = page.get_pixmap()
        image = Image.frombytes(
            "RGB", (temp_pix.width, temp_pix.height), temp_pix.samples
        )

        # Intermediate saving step to change the jpg quality (saved to buffer)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=jpg_quality)

        # Retrieve the buffer and insert that image to the original document
        image_data = buffer.getvalue()
        pix = fitz.Pixmap(image_data)
        doc[page_num].insert_image(page.rect, pixmap=pix)

    def lighten(self, doc: fitz.Document, page_num, severity: float):
        """Lighten an image, increasing its average brightness.

        Args:
            doc(fitz.Document): The target document.
            page_num(int): The target page number (0 indexed).
            severity(float): How much lighter the image gets.
        """
        page = doc[page_num]

        # Preserve quality of page
        matrix = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=matrix)
        pix.gamma_with(0.5 - severity * 0.5)
        page.insert_image(page.rect, pixmap=pix)

    def darken(self, doc: fitz.Document, page_num, severity: float):
        """Darken an image, decreasing its average brightness.

        Args:
            doc(fitz.Document): The target document.
            page_num(int): The target page number (0 indexed).
            severity(float): How much darker the image gets.
        """
        page = doc[page_num]

        # Preserve quality of page
        matrix = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1 - severity)

        bytestream = io.BytesIO()
        img.save(bytestream, "JPEG")
        page.insert_image(page.rect, stream=bytestream)

    def jam(self, doc: fitz.Document, page_num, severity: float):
        """Simulates a page feed error, where a row is smeared downwards.

        Args:
            doc(fitz.Document): The target document.
            page_num(int): The target page number.
            severity(float): The severity of the smear, which is how far up the page it starts.
        """
        page = doc[page_num]

        # Convert the page to PIL Image
        temp_pix = page.get_pixmap()
        image = Image.frombytes(
            "RGB", (temp_pix.width, temp_pix.height), temp_pix.samples
        )

        start_row = image.height - int(image.height * severity)
        cropbox = (0, start_row, image.width, start_row + 1)
        row_img = image.crop(cropbox)
        row_img = row_img.resize((image.width, image.height - start_row + 1))
        image.paste(row_img, (0, start_row - 1, image.width, image.height))

        bytestream = io.BytesIO()
        image.save(bytestream, "JPEG")
        page.insert_image(page.rect, stream=bytestream)

    def stretch(self, doc: fitz.Document, page_number: int, severity: float):
        """Stretch a page, expanding near the top and compressing near the bottom.

        The stretch works through non-linear shifting for the pixel in the y-direction (particularly shifting each pixel downward).

        This implementation uses the sine function (with a period of 2 * height), so that delta_y's sign is constant throughout
        the operation (negative in this case). Additionally, using a half sine wave as the shifter causes an increasing shifting magnitude
        from 0 to h/2 and a decreasing shifting magnitude from h/2 onward. The effect is caused by the increasing - decreasing magnitude of the y-shifts.
        Basically, everything tends to be stretched down (a pixel will be replaced by its upper peers, because of negative shift), so when the shifting magnitude is increasing
        and around its peak, the majority of the page will have been stretched down, leaving a small portion on the bottom (where the shifting magnitude is decreasing and is already small),
        and effectively creates a compression effect.

        Args:
            doc (fitz.Document): The document containing the page.
            page_number (int): The page number to be stretched (0 indexed).
            severity (float): The severity of the stretch.
        """
        page = self.get_page(doc, page_number)
        amplitude = 200 * severity
        pix = page.get_pixmap()
        pil_image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img: np.ndarray = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        # Handle different cases based on the shape of the image (to satisfy mypy)
        if len(img.shape) == 3:
            height, width, channels = img.shape  # Typical case for color images
        elif len(img.shape) == 2:
            height, width = img.shape  # Grayscale image
        else:
            raise ValueError(f"Unexpected shape for img: {img.shape}")

        img_output: np.ndarray = np.zeros(img.shape, dtype=np.uint8)
        for x in range(width):
            for y in range(height):
                # *Period is set to 2* height, such that delta_y's sign is constant
                # *The default sign is negative, such that the top page is
                # stretched and the bottom page is squashed.
                delta_y = -int(amplitude * math.sin(2 * math.pi * y / (2 * height)))
                if (y + delta_y) < height and (y + delta_y) >= 0:
                    img_output[y, x] = img[(y + delta_y), x]

        # Convert the numpy array back to a PIL Image
        pil_image_output = Image.fromarray(img_output)

        # Save the PIL image to a bytes buffer
        img_byte_arr = io.BytesIO()
        pil_image_output.save(img_byte_arr, format="PNG")
        img_byte_arr.seek(0)

        # Insert the image into the original page (overwriting the original content)
        img_data = img_byte_arr.read()  # Read image data from the buffer
        img_byte_arr.close()  # Close the buffer
        page.insert_image(fitz.Rect(0, 0, width, height), stream=img_data)

    def detect_qr_code_area(self, corner: str, page: fitz.Page) -> fitz.Rect:
        """Detects a single QR code area based on the specified corner.

        Args:
            corner (str): The corner to target.
            page (fitz.Page): The PDF page to analyze.

        Returns:
            fitz.Rect: The detected QR code area.
        """
        page_width = page.rect.width
        page_height = page.rect.height
        qr_area = None

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

    def qr_hide(self, page: fitz.Page, qr_area: fitz.Rect):
        """Covers an area of the page where a QR code might be located.

        Args:
            page (fitz.Page): The PDF page to alter.
            qr_area (fitz.Rect): Rectangle area to cover.
        """
        page.draw_rect(qr_area, color=(0, 0, 0), fill=(0, 0, 0))

    def qr_corrupt(self, page: fitz.Page, qr_area: fitz.Rect):
        """Corrupts an area of the page where a QR code might be located.

        Args:
            page (fitz.Page): The PDF page to alter.
            qr_area (fitz.Rect): Rectangle area to corrupt.
        """
        num_lines = 10
        for _ in range(num_lines):
            x1 = random.uniform(qr_area.x0, qr_area.x1)
            y1 = random.uniform(qr_area.y0, qr_area.y1)
            x2 = random.uniform(qr_area.x0, qr_area.x1)
            y2 = random.uniform(qr_area.y0, qr_area.y1)
            page.draw_line(
                fitz.Point(x1, y1), fitz.Point(x2, y2), color=(0, 0, 0), width=2
            )

    def muck_paper(
        self,
        filepath: str,
        page_number: int,
        operation: str,
        corner: str,
        severity: float,
        jaggedness: int = 2,
    ):
        """Muck a paper in the given path.

        Args:
            filepath: the path to the pdf.
            page_number: the page number to be mucked.
            operation: mucking operation.
            corner: which corner to be mucked.
            severity: float from (0, 1) representing how severe is the mucking.
            jaggedness: measure of jaggedness for tear operation.
        """
        # Open file
        file = fitz.open(filepath)

        # Manipulate file
        pages = [self.get_page(file, page_number)]
        if page_number % 2 == 0:
            other_page = page_number - 1
        else:
            other_page = page_number + 1

        if other_page <= file.page_count and other_page > 0:
            pages.append(self.get_page(file, other_page))

        # Perform the selected operation and add descriptive text
        if operation == "tear":
            self.tear_double_sided(pages, corner, severity, jaggedness)
            self.add_operation_description(pages[0], "tear", corner=corner)
            self.add_operation_description(pages[1], "tear", corner=corner)
        elif operation == "fold":
            self.fold_page(pages, corner, severity)
            self.add_operation_description(pages[0], "fold", corner=corner)
            self.add_operation_description(pages[1], "fold", corner=corner)
        elif operation == "rotate":
            self.rotate_page(file, page_number - 1, severity)
        elif operation == "compress":
            self.compress(file, page_number - 1, severity)
            self.add_operation_description(pages[0], "compress", corner=None)
        elif operation == "lighten":
            self.lighten(file, page_number - 1, severity)
            self.add_operation_description(pages[0], "lighten", corner=None)
        elif operation == "darken":
            self.darken(file, page_number - 1, severity)
            self.add_operation_description(pages[0], "darken", corner=None)
        elif operation == "jam":
            self.jam(file, page_number - 1, severity)
            self.add_operation_description(pages[0], "jam", corner=None)
        elif operation == "stretch":
            self.stretch(file, page_number, severity)
            self.add_operation_description(pages[0], "stretch", corner=None)
        elif operation == "hide":
            qr_area = self.detect_qr_code_area(corner, pages[0])
            self.qr_hide(pages[0], qr_area)
            self.add_operation_description(pages[0], "hide", corner=corner)
        elif operation == "corrupt":
            qr_area = self.detect_qr_code_area(corner, pages[0])
            self.qr_corrupt(pages[0], qr_area)
            self.add_operation_description(pages[0], "corrupt", corner=None)
        elif operation == "obscure":
            self.obscure_qr_codes_in_paper(file)
        else:
            raise RuntimeError("Invalid operation specified")

        file.saveIncr()
