# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from importlib import resources

import numpy
from PIL import Image

from django.contrib.auth.models import User
from django.test import TestCase

from plom.scan import QRextract
import plom_server.Scan.tests as _Scan_tests
from plom_server.Scan.services import ScanService
from ..services import RectangleExtractor

# from ..services.rectangle import _get_reference_rectangle


class RectangleServiceTests(TestCase):

    def test_rectangle_floats(self) -> None:
        img_path = resources.files(_Scan_tests) / "page_img_good.png"
        img = Image.open(img_path)  # type: ignore[arg-type]
        img_bytes = (resources.files(_Scan_tests) / "page_img_good.png").read_bytes()
        r = RectangleExtractor._get_largest_rectangle_contour(
            img_bytes, (img.width, img.height), (0, 0, 100, 100)
        )
        for k, v in r.items():
            self.assertIsInstance(k, str)
            self.assertIsInstance(v, float)
            self.assertNotIsInstance(v, numpy.float64)  # Issue #3870
        self.assertEqual(set(r.keys()), set(("top_f", "bottom_f", "left_f", "right_f")))

    def test_rectangle_find(self) -> None:
        img_path = resources.files(_Scan_tests) / "page_img_good.png"
        img = Image.open(img_path)  # type: ignore[arg-type]

        codes = QRextract(img_path)
        parsed_codes = ScanService.parse_qr_code([codes])
        # print(parsed_codes)
        # meh = _get_reference_rectangle(parsed_codes)
        # print(meh)
        x_coords = []
        y_coords = []
        for cnr in ["NE", "SE", "NW", "SW"]:
            if cnr in parsed_codes:
                x_coords.append(parsed_codes[cnr]["x_coord"])
                y_coords.append(parsed_codes[cnr]["y_coord"])
        # rectangle described by location of the 3 qr-code stamp centres of the reference image
        LEFT = min(x_coords)
        RIGHT = max(x_coords)
        TOP = min(y_coords)
        BOTTOM = max(y_coords)

        img_bytes = (resources.files(_Scan_tests) / "page_img_good.png").read_bytes()
        r = RectangleExtractor._get_largest_rectangle_contour(
            img_bytes, (img.width, img.height), (LEFT, TOP, RIGHT, BOTTOM)
        )
        print(r)
