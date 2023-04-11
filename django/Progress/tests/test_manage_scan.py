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

from Progress.services import ManageScanService


@skip(
    "Many of these tests need rebuilding once we rebuild UI for handling extra/unknowns/discards."
)
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

        # self.colliding_image = baker.make(
        #     CollidingImage,
        #     file_name=f"{settings.BASE_DIR}/media/page_images/colliding_pages/1/page1_abcdef.png",
        #     hash="abcdef",
        #     paper_number=1,
        #     page_number=1,
        #     bundle=self.bundle,
        #     bundle_order=1,
        # )
        return super().setUp()

    def test_discarded_image_path(self):
        """
        Test ManageScanService.get_discarded_image_path()
        """

        mss = ManageScanService()
        new_path = mss.get_discarded_image_path("abcde", make_dirs=False)
        self.assertEqual(
            str(new_path),
            f"{settings.BASE_DIR}/media/page_images/discarded_pages/abcde.png",
        )

    def test_discard_colliding(self):
        """
        Test ManageScanService.discard_colliding_image()
        """

        mss = ManageScanService()
        mss.discard_colliding_image(self.colliding_image, make_dirs=False)
        discarded_image = DiscardedImage.objects.get(hash="abcdef")

        self.assertEqual(discarded_image.hash, "abcdef")
        self.assertEqual(
            discarded_image.file_name,
            f"{settings.BASE_DIR}/media/page_images/discarded_pages/abcdef.png",
        )

    def test_replace_image(self):
        """
        Test ManageScanService.replace_image_with_colliding()
        """

        mss = ManageScanService()
        mss.replace_image_with_colliding(
            self.image,
            self.colliding_image,
            make_dirs=False,
        )

        new_image = Image.objects.get(hash="abcdef")
        self.assertEqual(
            str(new_image.file_name),
            f"{settings.BASE_DIR}/media/page_images/test_papers/1/page1.png",
        )

        discarded = DiscardedImage.objects.get(hash="lmnop")
        self.assertEqual(
            str(discarded.file_name),
            f"{settings.BASE_DIR}/media/page_images/discarded_pages/lmnop.png",
        )

    def test_restore_colliding_image(self):
        """
        Test ManageScanService.restore_colliding_image()
        """

        mss = ManageScanService()
        mss.discard_colliding_image(self.colliding_image, make_dirs=False)

        self.assertEqual(len(CollidingImage.objects.all()), 0)

        discarded = mss.get_discarded_image("abcdef")
        restored = mss.restore_colliding_image(discarded, make_dirs=False)

        self.assertEqual(len(DiscardedImage.objects.all()), 0)
        self.assertEqual(len(CollidingImage.objects.all()), 1)
        self.assertEqual(
            str(restored.file_name),
            f"{settings.BASE_DIR}/media/page_images/colliding_pages/1/page1_abcdef.png",
        )
        self.assertEqual(restored.paper_number, 1)
        self.assertEqual(restored.page_number, 1)

    def test_restore_replaced_image(self):
        """
        Test ManageScanService.restore_colliding_image() with a discarded page-image
        """

        mss = ManageScanService()
        mss.replace_image_with_colliding(
            self.image, self.colliding_image, make_dirs=False
        )

        discarded = mss.get_discarded_image("lmnop")
        restored = mss.restore_colliding_image(discarded, make_dirs=False)

        self.assertEqual(len(DiscardedImage.objects.all()), 0)
        self.assertEqual(len(CollidingImage.objects.all()), 1)
        self.assertEqual(
            str(restored.file_name),
            f"{settings.BASE_DIR}/media/page_images/colliding_pages/1/page1_lmnop.png",
        )
        self.assertEqual(restored.paper_number, 1)
        self.assertEqual(restored.page_number, 1)

        image = Image.objects.get(hash="abcdef")
        self.assertEqual(type(image), Image)
