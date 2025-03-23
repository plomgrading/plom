# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from importlib import resources

from django.test import TestCase
import numpy
from PIL import Image

from plom.scan import QRextract
import plom_server.Scan.tests as _Scan_tests
from plom_server.Scan.services import ScanService
from ..services import RectangleExtractor

from ..services.rectangle import _get_reference_rectangle


class RectangleServiceTests(TestCase):

    def test_rectangle_floats(self) -> None:
        img_path = resources.files(_Scan_tests) / "page_img_good.png"
        img = Image.open(img_path)  # type: ignore[arg-type]
        img_size = (img.width, img.height)
        img_bytes = img_path.read_bytes()
        r = RectangleExtractor._get_largest_rectangle_contour(
            img_bytes, img_size, (0, 0, 100, 100)
        )
        assert r is not None
        for k, v in r.items():
            self.assertIsInstance(k, str)
            self.assertIsInstance(v, float)
            self.assertNotIsInstance(v, numpy.float64)  # Issue #3870
        self.assertEqual(set(r.keys()), set(("top_f", "bottom_f", "left_f", "right_f")))

    def test_rectangle_find(self) -> None:
        img_path = resources.files(_Scan_tests) / "page_img_good.png"
        img = Image.open(img_path)  # type: ignore[arg-type]
        img_size = (img.width, img.height)
        img_bytes = img_path.read_bytes()
        ref_rect = (0, 0, img_size[0], img_size[1])

        # given the whole image, we find *some* rectangle
        r = RectangleExtractor._get_largest_rectangle_contour(
            img_bytes, img_size, ref_rect
        )
        assert r is not None
        self.assertEqual(set(r.keys()), set(("top_f", "bottom_f", "left_f", "right_f")))

        # coor sys increases as we go down so bottom bigger than top
        self.assertGreater(r["bottom_f"], r["top_f"])

        # Find rectangle in the lower right
        region = {"left_f": 0.7, "top_f": 0.7, "right_f": 1.0, "bottom_f": 1.0}
        r = RectangleExtractor._get_largest_rectangle_contour(
            img_bytes, img_size, ref_rect, region=region
        )
        assert r is not None
        ratio = (r["right_f"] - r["left_f"]) / (r["bottom_f"] - r["top_f"])
        # not a square b/c we're in [0,1]^2 coord system
        assert 1.3 < ratio < 1.5, f"not close to square: ratio={ratio}"

        # search the top middle to find the boxed text
        region = {"left_f": 0.2, "top_f": 0, "right_f": 0.8, "bottom_f": 0.2}
        r = RectangleExtractor._get_largest_rectangle_contour(
            img_bytes, img_size, ref_rect, region=region
        )
        assert r is not None
        self.assertAlmostEqual(r["left_f"], 0.32, delta=0.04)
        self.assertAlmostEqual(r["right_f"], 0.65, delta=0.04)
        self.assertAlmostEqual(r["top_f"], 0.04, delta=0.01)
        self.assertAlmostEqual(r["bottom_f"], 0.07, delta=0.01)

        # no box in the bottom middle
        region = {"left_f": 0.2, "top_f": 0.9, "right_f": 0.8, "bottom_f": 1.0}
        r = RectangleExtractor._get_largest_rectangle_contour(
            img_bytes, img_size, ref_rect, region=region
        )
        self.assertIsNone(r)

    def test_rectangle_find_QR_coord_system(self) -> None:
        img_path = resources.files(_Scan_tests) / "page_img_good.png"
        img = Image.open(img_path)  # type: ignore[arg-type]
        img_size = (img.width, img.height)
        img_bytes = img_path.read_bytes()

        codes = QRextract(img_path)
        parsed_codes = ScanService.parse_qr_code([codes])
        rd = _get_reference_rectangle(parsed_codes)
        ref_rect = (rd["left"], rd["top"], rd["right"], rd["bottom"])

        # find the lower-right box around the QR code
        region = {"left_f": 0.9, "top_f": 0.9, "right_f": 1.1, "bottom_f": 1.1}
        r = RectangleExtractor._get_largest_rectangle_contour(
            img_bytes, img_size, ref_rect, region=region
        )
        assert r is not None
        self.assertAlmostEqual(r["left_f"], 0.93, delta=0.05)
        self.assertAlmostEqual(r["right_f"], 1.07, delta=0.05)
        self.assertAlmostEqual(r["top_f"], 0.94, delta=0.05)
        self.assertAlmostEqual(r["bottom_f"], 1.04, delta=0.05)
