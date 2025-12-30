# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
from model_bakery import baker
from ..models import StagingBundle, StagingImage


class ScanStagingImageTypesTests(TestCase):

    def setUp(self) -> None:
        scan_group: Group = baker.make(Group, name="scanner")
        user0: User = baker.make(User, username="user0")
        user0.groups.add(scan_group)
        user0.save()
        self.bundle = baker.make(StagingBundle, user=user0, slug="testbundle")

    def test_illegal_stagingimage_errors(self) -> None:
        with self.assertRaisesRegex(ValidationError, "KNOWN .* paper_number"):
            baker.make(
                StagingImage,
                bundle=self.bundle,
                bundle_order=1,
                image_type=StagingImage.KNOWN,
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
