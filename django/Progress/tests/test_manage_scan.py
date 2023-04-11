# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

from django.test import TestCase
from django.conf import settings
from model_bakery import baker
from unittest import skip


from Papers.models import (
    Image,
    DNMPage,
    Bundle,
)
from Scan.models import StagingImage, StagingBundle


class ManageScanTests(TestCase):
    """
    Tests for Progress.services.ManageScanService()
    """

    def setUp(self):
        self.bundle = baker.make(
            Bundle,
            hash="qwerty",
        )

        self.staged_image = baker.make(
            StagingImage,
            bundle=baker.make(StagingBundle, pdf_hash="qwerty"),
            bundle_order=1,
        )

        self.image = baker.make(
            Image,
            hash="lmnop",
            file_name=f"{settings.BASE_DIR}/media/page_images/test_papers/1/page1.png",
        )

        self.page = baker.make(
            DNMPage,
            image=self.image,
        )

        return super().setUp()
