# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.test import TestCase
from django.core.exceptions import ValidationError
from model_bakery import baker
from ..models import StagingBundle, StagingImage


class ScanStagingImageTypesTests(TestCase):

    def setUp(self) -> None:
        self.bundle = baker.make(StagingBundle, slug="testbundle")

    def test_illegal_stagingimage_errors(self) -> None:
        with self.assertRaisesRegex(ValidationError, "KNOWN .* paper_number"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.KNOWN,
            )
        with self.assertRaisesRegex(ValidationError, "KNOWN .* page_number"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.KNOWN,
                paper_number=42,
            )
        with self.assertRaisesRegex(ValidationError, "KNOWN .* version"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.KNOWN,
                paper_number=42,
                page_number=42,
            )

        with self.assertRaisesRegex(ValidationError, "UNKNOWN .* not .* paper_number"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.UNKNOWN,
                paper_number=42,
            )
        with self.assertRaisesRegex(ValidationError, "UNKNOWN .* not .* page_number"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.UNKNOWN,
                page_number=42,
            )
        with self.assertRaisesRegex(ValidationError, "UNKNOWN .* not .* version"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.UNKNOWN,
                version=1,
            )
        with self.assertRaisesRegex(ValidationError, "EXTRA .* not .* page_number"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.EXTRA,
                page_number=42,
            )
        with self.assertRaisesRegex(ValidationError, "DISCARD .* discard_reason"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.DISCARD,
            )
        with self.assertRaisesRegex(ValidationError, "ERROR .* error_reason"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.ERROR,
            )

    def test_illegal_unread_stagingimage_errors(self) -> None:
        with self.assertRaisesRegex(ValidationError, "UNREAD .* not .* paper_number"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.UNREAD,
                paper_number=42,
            )
        with self.assertRaisesRegex(ValidationError, "UNREAD .* not .* page_number"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.UNREAD,
                page_number=42,
            )
        with self.assertRaisesRegex(ValidationError, "UNREAD .* not .* version"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.UNREAD,
                version=1,
            )

    def test_illegal_unread_stagingimage_qrcode_errors(self) -> None:
        with self.assertRaisesRegex(ValidationError, "UNREAD .* not .* parsed_qr"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.UNREAD,
                parsed_qr={"some": "dict"},
            )
        baker.make(
            StagingImage,
            bundle=self.bundle,
            bundle_order=2,
            image_type=StagingImage.UNREAD,
            parsed_qr={},
        )
        baker.make(
            StagingImage,
            bundle=self.bundle,
            bundle_order=3,
            image_type=StagingImage.UNREAD,
            parsed_qr=None,
        )

    def test_illegal_pushed_stagingimage_errors(self) -> None:
        with self.assertRaisesRegex(ValidationError, "UNREAD .* not .* pushed"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.UNREAD,
                pushed=True,
            )
        with self.assertRaisesRegex(ValidationError, "UNKNOWN .* not .* pushed"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.UNKNOWN,
                pushed=True,
            )

    def test_extra_stagingimage_flexibility_about_unknown_or_not(self) -> None:
        baker.make(
            StagingImage,
            bundle=self.bundle,
            bundle_order=1,
            image_type=StagingImage.EXTRA,
            question_idx_list=[1, 3],
            paper_number=42,
        )
        # This test could change in the future: both of these should not be errors
        # if we want to allow knowing either/or.
        with self.assertRaisesRegex(ValidationError, "EXTRA .* both"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.EXTRA,
                # question_idx_list=[1, 3],
                paper_number=42,
            )
        with self.assertRaisesRegex(ValidationError, "EXTRA .* both"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.EXTRA,
                question_idx_list=[1, 3],
                # paper_number=42,
            )
