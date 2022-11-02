# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.test import TestCase
from django.conf import settings
from model_bakery import baker

from Papers.services import ImageBundleService
from Papers.models import Bundle, Image, Paper, Specification, DNMPage, BasePage
from Scan.models import StagingImage, StagingBundle


class ImageBundleTests(TestCase):
    """
    Tests for Papers.services.ImageBundelService
    """

    def setUp(self):
        self.spec = baker.make(Specification)
        self.paper = baker.make(Paper, paper_number=1)
        self.page1 = baker.make(DNMPage, paper=self.paper, page_number=2)

        self.staged_bundle = baker.make(StagingBundle, pdf_hash="abcde")
        self.staged_image = baker.make(
            StagingImage,
            bundle=self.staged_bundle,
            bundle_order=1,
            file_name="page2.png",
            image_hash="abcdef",
            rotation=90,
        )

        return super().setUp()

    def test_create_bundle(self):
        """
        Test ImageBundlseService.create_bundle()
        """

        n_bundles = len(Bundle.objects.all())
        self.assertEqual(n_bundles, 0)

        ibs = ImageBundleService()
        ibs.create_bundle("bundle1", "abcde")

        n_bundles = len(Bundle.objects.all())
        self.assertEqual(n_bundles, 1)

        with self.assertRaises(RuntimeError):
            ibs.create_bundle("bundle2", "abcde")

        n_bundles = len(Bundle.objects.all())
        self.assertEqual(n_bundles, 1)

    def test_get_path(self):
        """
        Test ImageBundleService.get_page_image_path()
        """

        ibs = ImageBundleService()
        image_path = ibs.get_page_image_path(1, "page1.png", False)
        gold_path = (
            settings.BASE_DIR
            / "media"
            / "page_images"
            / "test_papers"
            / "1"
            / "page1.png"
        )
        self.assertEqual(str(gold_path), image_path)

    def test_push_good_image(self):
        """
        Test ImageBundleService._push_staged_image()
        """

        ibs = ImageBundleService()
        ibs._push_staged_image.call_local(self.staged_image, 1, 2, False)

        self.assertTrue(Bundle.objects.filter(hash="abcde").exists())

        img = Image.objects.get(hash="abcdef")
        self.assertEqual(img.bundle.hash, "abcde")
        self.assertEqual(img.bundle_order, 1)

        page = BasePage.objects.get(image=img)
        self.assertEqual(type(page), DNMPage)
        self.assertEqual(page.paper, self.paper)
        self.assertEqual(page.page_number, 2)

    def test_push_image_no_test(self):
        """
        Test that pushing an image to a nonexistent test-paper raises a RuntimeError.
        """

        ibs = ImageBundleService()

        with self.assertRaisesMessage(
            RuntimeError, "Test paper 2 is not in the database."
        ):
            ibs._push_staged_image.call_local(self.staged_image, 2, 2, False)

    def test_push_colliding_image(self):
        """
        Test that pushing a colliding page image raises a RuntimeError.
        """

        ibs = ImageBundleService()
        ibs._push_staged_image.call_local(self.staged_image, 1, 2, False)

        another_image = baker.make(StagingImage)
        with self.assertRaisesMessage(
            RuntimeError, "Collision page detected: test 1 already has page 2."
        ):
            ibs._push_staged_image.call_local(another_image, 1, 2, False)

    def test_push_identical_image(self):
        """
        Test that pushing a page with an existing hash raised a RuntimeError.
        """

        ibs = ImageBundleService()
        ibs._push_staged_image.call_local(self.staged_image, 1, 2, False)

        with self.assertRaisesMessage(
            RuntimeError, "Page image already exists in the database."
        ):
            ibs._push_staged_image.call_local(self.staged_image, 1, 3, False)
