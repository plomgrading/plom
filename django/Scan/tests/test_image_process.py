# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Natalie Balashov

from django.test import TestCase
from django.conf import settings

import pathlib
import tempfile
import cv2 as cv
from PIL import Image

from Scan.services import PageImageProcessor, ScanService
from plom.scan import QRextract


class PageImageProcessorTests(TestCase):
    """
    Test the functions in services.PageImageProcessor
    """

    def setUp(self):
        self.upright_page_full = {
            "NE": {"quadrant": "1"},
            "NW": {"quadrant": "2"},
            "SE": {"quadrant": "4"},
            "SW": {"quadrant": "3"},
        }

        self.upright_page_flaky = {"NE": {"quadrant": "1"}}

        self.turned_left_page_full = {
            "NE": {"quadrant": "4"},
            "NW": {"quadrant": "1"},
            "SE": {"quadrant": "3"},
            "SW": {"quadrant": "2"},
        }

        self.turned_left_page_flaky = {
            "NW": {"quadrant": "1"},
            "SE": {"quadrant": "3"},
        }

        self.turned_right_page_full = {
            "NE": {"quadrant": "2"},
            "NW": {"quadrant": "3"},
            "SE": {"quadrant": "1"},
            "SW": {"quadrant": "4"},
        }

        self.turned_right_page_flaky = {
            "NE": {"quadrant": "2"},
            "NW": {"quadrant": "3"},
            "SW": {"quadrant": "4"},
        }

        self.upside_down_page_full = {
            "NE": {"quadrant": "3"},
            "NW": {"quadrant": "4"},
            "SE": {"quadrant": "2"},
            "SW": {"quadrant": "1"},
        }

        self.upside_down_page_flaky = {
            "SW": {"quadrant": "1"},
        }

        self.bogus_page = {
            "NE": {"quadrant": "4"},
            "NW": {"quadrant": "3"},
            "SE": {"quadrant": "2"},
            "SW": {"quadrant": "1"},
        }

        self.qr_dict = {
            "NW": {
                "x_coord": 181.0,
                "y_coord": 387.5,
            },
            "SW": {
                "x_coord": 325.75,
                "y_coord": 3006.75,
            },
            "SE": {
                "x_coord": 2289.5,
                "y_coord": 2892.5,
            },
        }

        return super().setUp()

    def test_check_corner(self):
        """
        Test PageImageProcessor.check_corner()
        """
        pipr = PageImageProcessor()
        orientation = pipr.check_corner(
            val_from_qr="1",
            upright="1",
            turned_right="2",
            turned_left="4",
            upside_down="3",
        )
        self.assertEqual(orientation, "upright")

    def test_get_page_orientation(self):
        """
        Test PageImageProcessor.get_page_orientation()
        """
        pipr = PageImageProcessor()

        upright = pipr.get_page_orientation(self.upright_page_full)
        upright_flaky = pipr.get_page_orientation(self.upright_page_flaky)
        self.assertEqual(upright, "upright")
        self.assertEqual(upright_flaky, "upright")

        turned_left = pipr.get_page_orientation(self.turned_left_page_full)
        turned_left_flaky = pipr.get_page_orientation(self.turned_left_page_flaky)
        self.assertEqual(turned_left, "turned_left")
        self.assertEqual(turned_left_flaky, "turned_left")

        turned_right = pipr.get_page_orientation(self.turned_right_page_full)
        turned_right_flaky = pipr.get_page_orientation(self.turned_right_page_flaky)
        self.assertEqual(turned_right, "turned_right")
        self.assertEqual(turned_right_flaky, "turned_right")

        upside_down = pipr.get_page_orientation(self.upside_down_page_full)
        upside_down_flaky = pipr.get_page_orientation(self.upside_down_page_flaky)
        self.assertEqual(upside_down, "upside_down")
        self.assertEqual(upside_down_flaky, "upside_down")

        with self.assertRaises(RuntimeError):
            pipr.get_page_orientation(self.bogus_page)

        with self.assertRaises(RuntimeError):
            pipr.get_page_orientation({})

    def test_apply_image_transformation(self):
        """
        Test PageImageProcessor.apply_image_transformation()
        """
        pipr = PageImageProcessor()
        curr_dir = settings.BASE_DIR / "Scan" / "tests"
        img_path = curr_dir / "id_page_img.png"
        test_img = Image.open(img_path)

        # with tempfile.TemporaryDirectory() as tmpdir:
        if True:
            img_rot_path = curr_dir / "rot_3_deg_img.png"
            img_rot = test_img.rotate(3, expand=True)
            img_rot.save(img_rot_path)

            codes = QRextract(img_rot_path)
            scanner = ScanService()
            qr_dict_id = scanner.parse_qr_code([codes])

            img_cv = cv.imread(str(img_rot_path))

            # Image.fromarray(cv.cvtColor(img_cv, cv.COLOR_BGR2RGB)).show()
            cv.imwrite(str(curr_dir / "3_deg_img_before_transformation.png"), img_cv)

            transformed_img = pipr.apply_image_transformation(img_cv, qr_dict_id)

            # Image.fromarray(cv.cvtColor(transformed_img, cv.COLOR_BGR2RGB)).show()
            output_path = curr_dir / "3_deg_img_after_transformation.png"
            cv.imwrite(str(output_path), transformed_img)

    def test_extract_rectangular_region(self):
        """
        Test PageImageProcessor.extract_rectangular_region()
        """
        in_top = 0.28
        in_bottom = 0.58
        in_left = 0.09
        in_right = 0.91
        pipr = PageImageProcessor()
        curr_dir = settings.BASE_DIR / "Scan" / "tests"
        img_path = curr_dir / "id_page_img.png"

        test_img = Image.open(img_path)
        cropped_img = test_img.crop(
            (
                round(pipr.LEFT + in_left * pipr.WIDTH),
                round(pipr.TOP + in_top * pipr.HEIGHT),
                round(pipr.LEFT + in_right * pipr.WIDTH),
                round(pipr.TOP + in_bottom * pipr.HEIGHT),
            )
        )
        cropped_img.save(curr_dir / "unrotated_cropped.png")

        # with tempfile.TemporaryDirectory() as tmpdir:
        if True:
            img_rot_path = curr_dir / "rot_3_deg_img.png"
            img_rot = test_img.rotate(3, expand=True)
            img_rot.save(img_rot_path)

            codes = QRextract(img_rot_path)
            scanner = ScanService()
            qr_dict_id = scanner.parse_qr_code([codes])

            output_img = pipr.extract_rectangular_region(
                img_rot_path, 0, qr_dict_id, in_top, in_bottom, in_left, in_right
            )
            output_path = curr_dir / "rotated_and_corrected_cropped.png"
            output_img.save(output_path)

    def test_affine_transform_zero_correction(self):
        """
        Check whether OpenCV does strange things with images that don't need correction.
        """
        pipr = PageImageProcessor()
        curr_dir = settings.BASE_DIR / "Scan" / "tests"
        img_path = curr_dir / "id_page_img.png"
        codes = QRextract(img_path)
        scanner = ScanService()
        qr_dict_no_rot = scanner.parse_qr_code([codes])

        img_cv = cv.imread(str(img_path))
        # Image.fromarray(cv.cvtColor(img_cv, cv.COLOR_BGR2RGB)).show()
        transformed_img = pipr.apply_image_transformation(img_cv, qr_dict_no_rot)
        # Image.fromarray(cv.cvtColor(transformed_img, cv.COLOR_BGR2RGB)).show()
        output_path = curr_dir / "no_correction_after_transformation.png"
        cv.imwrite(str(output_path), transformed_img)

    def test_affine_transform_15_degree_rot(self):
        """
        Check cv.warpAffine() on an image with a 15-degree rotation.
        """
        pipr = PageImageProcessor()
        curr_dir = settings.BASE_DIR / "Scan" / "tests"
        img_path = curr_dir / "id_page_img.png"
        test_img = Image.open(img_path)

        img_rot_path = curr_dir / "rot_15_deg_img.png"
        img_rot = test_img.rotate(15, expand=True)
        img_rot.save(img_rot_path)

        codes = QRextract(img_rot_path)
        scanner = ScanService()
        qr_dict_id = scanner.parse_qr_code([codes])

        img_cv = cv.imread(str(img_rot_path))
        # Image.fromarray(cv.cvtColor(img_cv, cv.COLOR_BGR2RGB)).show()
        transformed_img = pipr.apply_image_transformation(img_cv, qr_dict_id)
        # Image.fromarray(cv.cvtColor(transformed_img, cv.COLOR_BGR2RGB)).show()
        output_path = curr_dir / "15_deg_after_transformation.png"
        cv.imwrite(str(output_path), transformed_img)
