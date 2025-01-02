# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

import pathlib
import random
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any

import exif
import pymupdf as fitz
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.test import TestCase
from django.utils import timezone
from model_bakery import baker
from PIL import Image

from plom.scan import QRextract, pdfmucker, rotate

from .. import tests as _Scan_tests
from ..models import StagingBundle, StagingImage
from ..services import PageImageProcessor, ScanService


class ScanServiceTests(TestCase):
    # This test does unpleasant things, see Issue #2925.
    def setUp(self) -> None:
        random_user_name = f"__tests_user{random.randint(0, 99999)}"
        self.user: User = baker.make(User, username=random_user_name)
        self.pdf_path = pdfmucker.generate_dummy_pdf()
        media_folder = settings.MEDIA_ROOT
        media_folder.mkdir(exist_ok=True)

    def tearDown(self) -> None:
        # TODO: if you have a collision with a real user, this may destroy their files
        # shutil.rmtree(
        #     settings.MEDIA_ROOT / "staging/bundles/" / self.user.username,
        #     ignore_errors=True,
        # )
        (settings.MEDIA_ROOT / "staging/bundles/" / self.user.username).rmdir()

    def test_upload_bundle(self) -> None:
        """Test ScanService.upload_bundle and assert uploaded PDF file saved to right place."""
        scanner = ScanService()
        timestamp = timezone.now().timestamp()
        # open the pdf-file to create a file-object to pass to the upload command.
        with open(self.pdf_path, "rb") as fh:
            pdf_file_object = File(fh)

        slug = "_test_bundle"
        scanner.upload_bundle(pdf_file_object, slug, self.user, timestamp, "abcde", 28)

        the_bundle = StagingBundle.objects.get(user=self.user, slug=slug)
        bundle_path = pathlib.Path(the_bundle.pdf_file.path)
        self.assertEqual(
            bundle_path,
            settings.MEDIA_ROOT
            / "staging"
            / "bundles"
            / self.user.username
            / str(the_bundle.pk)
            / f"{timestamp}.pdf",
        )
        self.assertTrue(bundle_path.exists())
        # TODO: is this an appropriate way to cleanup?
        the_bundle.delete()
        bundle_path.unlink()
        bundle_path.parent.rmdir()

    def test_remove_bundle(self) -> None:
        """Test removing a bundle and assert uploaded PDF file removed from disk."""
        timestamp = timezone.now().timestamp()
        # make a pdf and save it to a tempfile
        with tempfile.NamedTemporaryFile() as ntf:
            with fitz.Document(self.pdf_path) as pdf:
                pdf.save(ntf.name)

            # open that file to get django to save it to disk as per the models File("upload_to")
            with ntf:
                bundle = StagingBundle(
                    slug="_test_bundle",
                    pdf_file=File(ntf, name=f"{timestamp}.pdf"),
                    user=self.user,
                    timestamp=timestamp,
                    pdf_hash="abcde",
                    has_page_images=False,
                )
                bundle.save()
        # the pdf should now have been saved to the upload-to of the bundle-object
        bundle_path = pathlib.Path(bundle.pdf_file.path)
        self.assertTrue(bundle_path.exists())
        # now remove it using the scan services
        scanner = ScanService()
        scanner.remove_bundle_by_pk(bundle.pk)
        # that path should no longer exist, nor should the bundle
        self.assertFalse(bundle_path.exists())
        self.assertFalse(StagingBundle.objects.exists())
        bundle_path.parent.rmdir()


class MoreScanServiceTests(TestCase):
    def test_duplicate_hash(self) -> None:
        baker.make(StagingBundle, pdf_hash="abcde")
        scanner = ScanService()
        duplicate_detected = scanner.check_for_duplicate_hash("abcde")
        self.assertTrue(duplicate_detected)

    def test_parse_qr_codes(self) -> None:
        """Test QR codes read and parsed correctly."""
        img_path = resources.files(_Scan_tests) / "page_img_good.png"
        codes = QRextract(img_path)
        scanner = ScanService()
        parsed_codes = scanner.parse_qr_code([codes])

        assert parsed_codes
        code_dict: dict[str, dict[str, Any]] = {
            "NW": {
                "page_info": {
                    "paper_id": 6,
                    "page_num": 4,
                    "version_num": 1,
                    "public_code": "93849",
                },
                "quadrant": "2",
                "tpv": "00006004001",
                "x_coord": 166.5,
                "y_coord": 272,
            },
            "SW": {
                "page_info": {
                    "paper_id": 6,
                    "page_num": 4,
                    "version_num": 1,
                    "public_code": "93849",
                },
                "quadrant": "3",
                "tpv": "00006004001",
                "x_coord": 173.75,
                "y_coord": 2895.5,
            },
            "SE": {
                "page_info": {
                    "paper_id": 6,
                    "page_num": 4,
                    "version_num": 1,
                    "public_code": "93849",
                },
                "quadrant": "4",
                "tpv": "00006004001",
                "x_coord": 2141,
                "y_coord": 2883.5,
            },
        }
        for quadrant in code_dict.keys():
            self.assertEqual(
                parsed_codes[quadrant]["page_info"]["paper_id"],
                code_dict[quadrant]["page_info"]["paper_id"],
            )
            self.assertEqual(
                parsed_codes[quadrant]["page_info"]["page_num"],
                code_dict[quadrant]["page_info"]["page_num"],
            )
            self.assertEqual(
                parsed_codes[quadrant]["page_info"]["version_num"],
                code_dict[quadrant]["page_info"]["version_num"],
            )
            self.assertEqual(
                parsed_codes[quadrant]["page_info"]["public_code"],
                code_dict[quadrant]["page_info"]["public_code"],
            )
            self.assertEqual(
                parsed_codes[quadrant]["tpv"],
                code_dict[quadrant]["tpv"],
            )
            self.assertTrue(
                (parsed_codes[quadrant]["x_coord"] - code_dict[quadrant]["x_coord"])
                / code_dict[quadrant]["x_coord"]
                < 0.01
            )
            self.assertTrue(
                (parsed_codes[quadrant]["y_coord"] - code_dict[quadrant]["y_coord"])
                / code_dict[quadrant]["y_coord"]
                < 0.01
            )

    def test_parse_qr_codes_png_rotated_180(self) -> None:
        """Test QR codes read correctly after rotation."""
        scanner = ScanService()

        image_upright_path = resources.files(_Scan_tests) / "page_img_good.png"
        qrs_upright = QRextract(image_upright_path)
        codes_upright = scanner.parse_qr_code([qrs_upright])
        # mypy complains about Traversable
        assert isinstance(image_upright_path, (Path, resources.abc.Traversable))
        image_upright = Image.open(image_upright_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            image_flipped_path = pathlib.Path(tmpdir) / "flipped.png"
            image_flipped = image_upright.rotate(180)
            image_flipped.save(image_flipped_path)

            qrs_flipped = QRextract(image_flipped_path)
            codes_flipped = scanner.parse_qr_code([qrs_flipped])

            pipr = PageImageProcessor()
            rotation = pipr.get_rotation_angle_from_QRs(codes_flipped)
            self.assertEqual(rotation, 180)

            # read QR codes a second time due to rotation of image
            qrs_flipped = QRextract(image_flipped_path, rotation=rotation)
            codes_flipped = scanner.parse_qr_code([qrs_flipped])

        xy_upright = []
        xy_flipped = []

        for q, p in zip(codes_upright, codes_flipped):
            xy_upright.append(
                [codes_upright[q]["x_coord"], codes_upright[q]["y_coord"]]
            )
            xy_flipped.append(
                [codes_flipped[p]["x_coord"], codes_flipped[p]["y_coord"]]
            )

        for original, rotated in zip(xy_upright, xy_flipped):
            self.assertTrue((original[0] - rotated[0]) / rotated[0] < 0.01)
            self.assertTrue((original[1] - rotated[1]) / rotated[1] < 0.01)

    def test_parse_qr_codes_jpeg_rotated_180_no_exif(self) -> None:
        """Test QR codes are read correctly, after rotating an upside-down jpeg page image with no exif."""
        scanner = ScanService()

        image_original_path = resources.files(_Scan_tests) / "page_img_good.png"
        qrs_original = QRextract(image_original_path)
        codes_original = scanner.parse_qr_code([qrs_original])
        # mypy complains about Traversable
        assert isinstance(image_original_path, (Path, resources.abc.Traversable))
        image_original = Image.open(image_original_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            image_flipped_path = pathlib.Path(tmpdir) / "flipped_no_exif.jpeg"
            image_flipped = image_original.rotate(180)
            image_flipped.save(image_flipped_path)
            with open(image_flipped_path, "rb") as f:
                im = exif.Image(f)
            assert not im.has_exif

            qrs_flipped = QRextract(image_flipped_path)
            codes_flipped = scanner.parse_qr_code([qrs_flipped])

            pipr = PageImageProcessor()
            rotation = pipr.get_rotation_angle_from_QRs(codes_flipped)
            self.assertEqual(rotation, 180)

            with open(image_flipped_path, "rb") as f:
                im = exif.Image(f)
            assert not im.has_exif

            # read QR codes a second time due to rotation of image
            qrs_flipped = QRextract(image_flipped_path, rotation=rotation)
            codes_flipped = scanner.parse_qr_code([qrs_flipped])

            xy_upright = []
            xy_flipped = []

            for q, p in zip(codes_original, codes_flipped):
                xy_upright.append(
                    [codes_original[q]["x_coord"], codes_original[q]["y_coord"]]
                )
                xy_flipped.append(
                    [codes_flipped[p]["x_coord"], codes_flipped[p]["y_coord"]]
                )

            for upright, rotated in zip(xy_upright, xy_flipped):
                self.assertTrue((upright[0] - rotated[0]) / rotated[0] < 0.01)
                self.assertTrue((upright[1] - rotated[1]) / rotated[1] < 0.01)

    def test_parse_qr_codes_jpeg_upright_exif_rot_180(self) -> None:
        """Test QR codes are read correctly after an upright page image with exif rotation of 180 is rotated."""
        scanner = ScanService()

        image_original_path = resources.files(_Scan_tests) / "page_img_good.png"
        # mypy complains about Traversable
        assert isinstance(image_original_path, (Path, resources.abc.Traversable))
        image_original = Image.open(image_original_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            image_exif_180_path = pathlib.Path(tmpdir) / "upright_exif_180.jpeg"
            image_original.save(image_exif_180_path)
            rotate.rotate_bitmap_jpeg_exif(image_exif_180_path, 180)
            with open(image_exif_180_path, "rb") as f:
                orig_im = exif.Image(f)
            self.assertEqual(orig_im.get("orientation"), exif.Orientation.BOTTOM_RIGHT)

            qrs_exif_180 = QRextract(image_exif_180_path)
            codes_exif_180 = scanner.parse_qr_code([qrs_exif_180])

            pipr = PageImageProcessor()
            rotation = pipr.get_rotation_angle_from_QRs(codes_exif_180)
            self.assertEqual(rotation, 180)

            with open(image_exif_180_path, "rb") as f:
                im = exif.Image(f)
            self.assertEqual(im.get("orientation"), orig_im.get("orientation"))

    def test_parse_qr_codes_jpeg_upside_down_exif_180(self) -> None:
        """Test ScanService.parse_qr_code() when image is upside down, but exif indicates 180 rotation."""
        scanner = ScanService()

        image_original_path = resources.files(_Scan_tests) / "page_img_good.png"
        qrs_original = QRextract(image_original_path)
        codes_original = scanner.parse_qr_code([qrs_original])
        # mypy complains about Traversable
        assert isinstance(image_original_path, (Path, resources.abc.Traversable))
        image_original = Image.open(image_original_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            image_flipped_path = pathlib.Path(tmpdir) / "flipped_exif_180.jpeg"
            image_flipped = image_original.rotate(180)
            image_flipped.save(image_flipped_path)
            rotate.rotate_bitmap_jpeg_exif(image_flipped_path, 180)
            with open(image_flipped_path, "rb") as f:
                orig_im = exif.Image(f)
            self.assertEqual(orig_im.get("orientation"), exif.Orientation.BOTTOM_RIGHT)

            qrs_flipped = QRextract(image_flipped_path)
            codes_flipped = scanner.parse_qr_code([qrs_flipped])

            pipr = PageImageProcessor()
            rotation = pipr.get_rotation_angle_from_QRs(codes_flipped)
            self.assertEqual(rotation, 0)

            with open(image_flipped_path, "rb") as f:
                im = exif.Image(f)
            self.assertEqual(im.get("orientation"), orig_im.get("orientation"))

            xy_upright = []
            xy_flipped = []

            for q, p in zip(codes_original, codes_flipped):
                xy_upright.append(
                    [codes_original[q]["x_coord"], codes_original[q]["y_coord"]]
                )
                xy_flipped.append(
                    [codes_flipped[p]["x_coord"], codes_flipped[p]["y_coord"]]
                )

            for original, rotated in zip(xy_upright, xy_flipped):
                self.assertTrue((original[0] - rotated[0]) / rotated[0] < 0.01)
                self.assertTrue((original[1] - rotated[1]) / rotated[1] < 0.01)

    def test_parse_qr_codes_jpeg_exif_90(self) -> None:
        """Test ScanService.parse_qr_code() when image exif indicates 90 counterclockwise rotation."""
        scanner = ScanService()

        image_original_path = resources.files(_Scan_tests) / "page_img_good.png"
        qrs_original = QRextract(image_original_path)
        codes_original = scanner.parse_qr_code([qrs_original])
        # mypy complains about Traversable
        assert isinstance(image_original_path, (Path, resources.abc.Traversable))
        image_original = Image.open(image_original_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            image_exif_90_path = pathlib.Path(tmpdir) / "rot_exif_90.jpeg"
            image_original.save(image_exif_90_path)
            rotate.rotate_bitmap_jpeg_exif(image_exif_90_path, 90)
            with open(image_exif_90_path, "rb") as f:
                orig_im = exif.Image(f)
            self.assertEqual(orig_im.get("orientation"), exif.Orientation.LEFT_BOTTOM)

            qrs_90_rot = QRextract(image_exif_90_path)
            codes_90_rot = scanner.parse_qr_code([qrs_90_rot])

            pipr = PageImageProcessor()
            rotation = pipr.get_rotation_angle_from_QRs(codes_90_rot)
            self.assertEqual(rotation, -90)

            with open(image_exif_90_path, "rb") as f:
                im = exif.Image(f)
            self.assertEqual(im.get("orientation"), orig_im.get("orientation"))

            # read QR codes a second time due to rotation of image
            qrs_90_rot = QRextract(image_exif_90_path, rotation=rotation)
            codes_90_rot = scanner.parse_qr_code([qrs_90_rot])

            xy_upright = []
            xy_90_rot = []

            for q, p in zip(codes_original, codes_90_rot):
                xy_upright.append(
                    [codes_original[q]["x_coord"], codes_original[q]["y_coord"]]
                )
                xy_90_rot.append(
                    [codes_90_rot[p]["x_coord"], codes_90_rot[p]["y_coord"]]
                )

            for original, rotated in zip(xy_upright, xy_90_rot):
                self.assertTrue((original[0] - rotated[0]) / rotated[0] < 0.01)
                self.assertTrue((original[1] - rotated[1]) / rotated[1] < 0.01)

    def test_known_images(self) -> None:
        """Test ``ScanService.get_all_known_images()``."""
        user: User = baker.make(User, username="user")
        scanner = ScanService()
        bundle = baker.make(
            StagingBundle, user=user, timestamp=timezone.now().timestamp()
        )
        # there are no images in the bundle
        imgs = scanner.get_all_known_images(bundle)
        self.assertEqual(imgs, [])

        # now make an image with no qr-codes, so known is false
        baker.make(
            StagingImage, parsed_qr={}, bundle=bundle, image_type=StagingImage.UNKNOWN
        )
        imgs = scanner.get_all_known_images(bundle)
        self.assertEqual(imgs, [])
        # now make an image with a qr-code and known=true.
        with_data = baker.make(
            StagingImage,
            parsed_qr={"dummy": "dict"},
            bundle=bundle,
            image_type=StagingImage.KNOWN,
        )
        imgs = scanner.get_all_known_images(bundle)
        self.assertEqual(imgs, [with_data])
