# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2025 Colin B. Macdonald

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from plom_server.Scan.models import (
    StagingBundle,
    StagingImage,
    KnownStagingImage,
    ExtraStagingImage,
    ErrorStagingImage,
)
from plom_server.Scan.services import QRService
from plom_server.Base.models import BaseImage
from plom_server.Base.services import Settings
from plom_server.Papers.services import SpecificationService
from plom_server.Papers.models import Paper, FixedPage, MobilePage


class QRServiceTest(TestCase):
    def setUp(self):

        # setup spec
        spec_dict = {
            "idPage": 1,
            "numberOfVersions": 2,
            "numberOfPages": 6,
            "totalMarks": 10,
            "numberOfQuestions": 2,
            "name": "papers_demo",
            "longName": "Papers Test",
            "doNotMarkPages": [2, 5, 6],
            "question": [
                {"pages": [3], "mark": 5},
                {"pages": [4], "mark": 5},
            ],
        }
        SpecificationService.install_spec_from_dict(spec_dict)
        Settings.set_public_code("123456")

        # setup paper and pages
        paper = Paper.objects.create(paper_number=1)
        FixedPage.objects.create(paper=paper, page_number=3, version=1)
        FixedPage.objects.create(paper=paper, page_number=4, version=1)
        FixedPage.objects.create(paper=paper, page_number=5, version=1)

        # Extra page and scrap
        MobilePage.objects.create(paper=paper, question_index=1)
        MobilePage.objects.create(paper=paper, question_index=1)

        # Create bundle
        self.bundle = StagingBundle.objects.create(has_qr_codes=True)
        self.bundle_unread_qr = StagingBundle.objects.create(has_qr_codes=False)
        self.invalid_bundle = StagingBundle.objects.create(has_qr_codes=True)
        self.invalid_bundle = StagingBundle.objects.create(has_qr_codes=True)
        self.invalid_bundle = StagingBundle.objects.create(has_qr_codes=True)

        # mock BaseImage
        def create_mock_image():
            file = BytesIO()
            image = Image.new("RGB", (1, 1), (0, 0, 0))
            image.save(file, "PNG")
            file.seek(0)
            mock_image = SimpleUploadedFile(
                name="test.png", content=file.read(), content_type="image/png"
            )
            return mock_image

        # Helper to add images with a given parsed_qr dict:
        def make_staging_img(bundle, parsed_qr, order=0):
            image_file = create_mock_image()
            baseImage = BaseImage.objects.create(image_file=image_file)

            img = StagingImage.objects.create(
                bundle=bundle,
                bundle_order=order,
                parsed_qr=parsed_qr,
                image_type=StagingImage.UNKNOWN,
                baseimage=baseImage,
            )
            return img

        # no-QR image
        self.img_no_qr = make_staging_img(self.bundle, parsed_qr={})

        # valid single TPV
        self.img_known = make_staging_img(
            self.bundle,
            parsed_qr={
                "NE": {
                    "tpv": "0000100301",
                    "page_type": "plom_qr",
                    "page_info": {
                        "public_code": "123456",
                        "paper_id": 1,
                        "page_num": 3,
                        "version_num": 1,
                    },
                }
            },
        )

        # extra page
        self.img_extra = make_staging_img(
            self.bundle, parsed_qr={"NE": {"tpv": "plomX", "page_type": "plom_extra"}}
        )
        # scrap
        self.img_scrap = make_staging_img(
            self.bundle, parsed_qr={"NE": {"tpv": "plomS", "page_type": "plom_scrap"}}
        )

        # bundle separator
        self.img_bundle_separator = make_staging_img(
            self.bundle,
            parsed_qr={"NE": {"tpv": "plomB", "page_type": "plom_bundle_separator"}},
        )

        # collision: two images with same TPV
        self.img_col1 = make_staging_img(
            self.bundle,
            parsed_qr={
                "NE": {
                    "tpv": "0000100401",
                    "page_type": "plom_qr",
                    "page_info": {
                        "public_code": "123456",
                        "paper_id": 1,
                        "page_num": 4,
                        "version_num": 1,
                    },
                }
            },
            order=2,
        )
        self.img_col2 = make_staging_img(
            self.bundle,
            parsed_qr={
                "NE": {
                    "tpv": "0000100401",
                    "page_type": "plom_qr",
                    "page_info": {
                        "public_code": "123456",
                        "paper_id": 1,
                        "page_num": 5,
                        "version_num": 1,
                    },
                }
            },
            order=3,
        )

        # Invalid bundles

        # Invalid_qr
        self.img_invalid_qr = make_staging_img(
            self.invalid_bundle,
            parsed_qr={
                "NE": {
                    "tpv": "0000100401",
                    "page_type": "invalid_qr",
                    "page_info": {
                        "public_code": "123456",
                        "paper_id": 1,
                        "page_num": 3,
                        "version_num": 1,
                    },
                }
            },
        )

        # Inconsistent page_types
        self.img_inconsistent_types = make_staging_img(
            self.invalid_bundle,
            parsed_qr={
                "NE": {
                    "tpv": "0000100401",
                    "page_type": "plom_qr",
                    "page_info": {"public_code": "123456"},
                },
                "NW": {
                    "tpv": "0000100401",
                    "page_type": "plomB",
                    "page_info": {"public_code": "123456"},
                },
            },
        )

    def test_classification(self):
        """Test QRService in classifying StagingImages."""
        QRService.classify_staging_images_based_on_QR_codes(self.bundle)

        # No-QR -> UNKNOWN
        img = StagingImage.objects.get(pk=self.img_no_qr.pk)
        self.assertEqual(img.image_type, StagingImage.UNKNOWN)

        # Known -> KNOWN + KnownStagingImage has correct fields
        img = StagingImage.objects.get(pk=self.img_known.pk)
        self.assertEqual(img.image_type, StagingImage.KNOWN)
        ks = KnownStagingImage.objects.get(staging_image=img)
        self.assertEqual(ks.paper_number, 1)
        self.assertEqual(ks.page_number, 3)
        self.assertEqual(ks.version, 1)

        # Extra -> EXTRA + ExtraStagingImage
        img = StagingImage.objects.get(pk=self.img_extra.pk)
        self.assertEqual(img.image_type, StagingImage.EXTRA)
        self.assertTrue(ExtraStagingImage.objects.filter(staging_image=img).exists())

        # Scrap -> DISCARD
        img = StagingImage.objects.get(pk=self.img_scrap.pk)
        self.assertEqual(img.image_type, StagingImage.DISCARD)

        # Bundle Separator -> DISCARD
        img = StagingImage.objects.get(pk=self.img_bundle_separator.pk)
        self.assertEqual(img.image_type, StagingImage.DISCARD)

        # Collision -> both images marked ERROR, with collision message
        for img in (self.img_col1, self.img_col2):
            img = StagingImage.objects.get(pk=img.pk)
            self.assertEqual(img.image_type, StagingImage.ERROR)
            err = ErrorStagingImage.objects.get(staging_image=img)
            self.assertIn("collides", err.error_reason)

    def test_bundle_no_qr(self):
        """Test exception is correctly raised when attempting to push unread QR bundle."""
        with self.assertRaises(ValueError):
            QRService.classify_staging_images_based_on_QR_codes(self.bundle_unread_qr)

    def test_invalid_bundles(self):
        """Test exception is correctly raised when there are invalid pages in the bundle."""
        QRService.classify_staging_images_based_on_QR_codes(self.invalid_bundle)

        # Invalid QR
        img = StagingImage.objects.get(pk=self.img_invalid_qr.pk)
        self.assertEqual(img.image_type, StagingImage.ERROR)
        err = ErrorStagingImage.objects.get(staging_image=img)
        self.assertIn("Invalid qr-code", err.error_reason)

        # Inconsistent page_types
        img = StagingImage.objects.get(pk=self.img_inconsistent_types.pk)
        self.assertEqual(img.image_type, StagingImage.ERROR)
        err = ErrorStagingImage.objects.get(staging_image=img)
        self.assertIn("Inconsistent qr-codes", err.error_reason)
