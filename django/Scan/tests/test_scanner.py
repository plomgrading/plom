# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Natalie Balashov

import fitz
import shutil
import pathlib
from datetime import datetime

from django.test import TestCase
from django.contrib.auth.models import User
from django.conf import settings
from model_bakery import baker

from plom.scan import QRextract
from Scan.services import ScanService
from Scan.models import StagingBundle, StagingImage


class ScanServiceTests(TestCase):
    def setUp(self):
        self.user0 = baker.make(User, username="user0")
        self.pdf = fitz.Document(
            settings.BASE_DIR / "Scan" / "tests" / "test_bundle.pdf"
        )
        media_folder = settings.BASE_DIR / "media"
        media_folder.mkdir(exist_ok=True)
        return super().setUp()

    def tearDown(self):
        shutil.rmtree(settings.BASE_DIR / "media" / "user0", ignore_errors=True)
        return super().tearDown()

    def test_upload_bundle(self):
        """
        Test ScanService.upload_bundle() and assert that the uploaded PDF file
        has been saved to the right place on disk.
        """

        scanner = ScanService()
        timestamp = datetime.now().timestamp()
        scanner.upload_bundle(self.pdf, "test_bundle", self.user0, timestamp, "abcde")

        the_bundle = StagingBundle.objects.get(user=self.user0, slug="test_bundle")
        bundle_path = the_bundle.file_path
        self.assertTrue(
            bundle_path,
            str(
                settings.BASE_DIR
                / "media"
                / "user0"
                / "bundles"
                / str(timestamp)
                / f"{timestamp}.pdf"
            ),
        )
        self.assertTrue(pathlib.Path(bundle_path).exists())

    def test_remove_bundle(self):
        """
        Test ScanService.remove_bundle() and assert that the uploaded PDF file
        has been removed from disk.
        """

        timestamp = datetime.now().timestamp()
        user_path = settings.BASE_DIR / "media" / "user0"
        user_path.mkdir(exist_ok=True)
        user_bundle_path = user_path / "bundles"
        user_bundle_path.mkdir(exist_ok=True)
        timestamp_path = user_bundle_path / str(timestamp)
        timestamp_path.mkdir(exist_ok=True)
        bundle_path = timestamp_path / f"{timestamp}.pdf"

        self.assertFalse(bundle_path.exists())

        bundle = StagingBundle(
            slug="test_bundle",
            file_path=bundle_path,
            user=self.user0,
            timestamp=timestamp,
            pdf_hash="abcde",
            has_page_images=False,
        )
        bundle.save()
        self.pdf.save(bundle_path)
        self.assertTrue(bundle_path.exists())

        scanner = ScanService()
        scanner.remove_bundle(timestamp, self.user0)
        self.assertFalse(bundle_path.exists())
        self.assertFalse(StagingBundle.objects.exists())

    def test_duplicate_hash(self):
        """
        Test ScanService.check_for_duplicate_hash()
        """
        baker.make(StagingBundle, pdf_hash="abcde")
        scanner = ScanService()
        duplicate_detected = scanner.check_for_duplicate_hash("abcde")
        self.assertTrue(duplicate_detected)

    def test_parse_qr_codes(self):
        """
        Test ScanService.parse_qr_code() and assert that the test QR codes
        have been successfully read and parsed into the correct format.
        """
        img_path = settings.BASE_DIR / "Scan" / "tests" / "page_img_good.png"
        codes = QRextract(img_path)
        scanner = ScanService()
        parsed_codes = scanner.parse_qr_code([codes])
        print(parsed_codes)
        code_dict = {
            "NW": {
                "paper_id": 6,
                "page_num": 4,
                "version_num": 1,
                "quadrant": "2",
                "public_code": "93849",
                "grouping_key": "00006004001",
            },
            "SW": {
                "paper_id": 6,
                "page_num": 4,
                "version_num": 1,
                "quadrant": "3",
                "public_code": "93849",
                "grouping_key": "00006004001",
            },
            "SE": {
                "paper_id": 6,
                "page_num": 4,
                "version_num": 1,
                "quadrant": "4",
                "public_code": "93849",
                "grouping_key": "00006004001",
            },
        }
        self.assertEqual(parsed_codes, code_dict)

    def test_complete_images(self):
        """
        Test ScanService.get_all_complete_images()
        """
        scanner = ScanService()
        bundle = baker.make(
            StagingBundle, user=self.user0, timestamp=datetime.now().timestamp()
        )

        imgs = scanner.get_all_complete_images(bundle)
        self.assertEqual(imgs, [])

        baker.make(StagingImage, parsed_qr={}, bundle=bundle)
        imgs = scanner.get_all_complete_images(bundle)
        self.assertEqual(imgs, [])

        with_data = baker.make(StagingImage, parsed_qr={"dummy": "dict"}, bundle=bundle)
        imgs = scanner.get_all_complete_images(bundle)
        self.assertEqual(imgs, [with_data])
