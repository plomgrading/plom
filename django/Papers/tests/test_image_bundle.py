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

    def test_all_staged_imgs_valid(self):
        """
        Test ImageBundleService.all_staged_imgs_valid().

        If the input collection of staging images is empty, return True.
        If there are one or more images that don't have all three of
            (page number, paper number, qr dict), return False.
        Otherwise, return True.
        """

        ibs = ImageBundleService()
        imgs = StagingImage.objects.all()
        self.assertTrue(ibs.all_staged_imgs_valid(imgs))

        for paper_num in range(2):
            for page_num in range(5):
                baker.make(
                    StagingImage,
                    paper_id=paper_num,
                    page_number=page_num,
                    parsed_qr={"NW": "Not empty!"},
                )

        imgs = StagingImage.objects.all()
        self.assertTrue(ibs.all_staged_imgs_valid(imgs))

        baker.make(StagingImage, paper_id=None, page_number=None, parsed_qr=None)
        imgs = StagingImage.objects.all()
        self.assertTrue(ibs.all_staged_imgs_valid(imgs))

    def test_find_internal_collisions(self):
        """
        Test ImageBundleService.find_internal_collisions()
        """

        ibs = ImageBundleService()
        imgs = StagingImage.objects.all()
        res = ibs.find_internal_collisions(imgs)
        self.assertEqual(res, [])

        paper1 = baker.make(StagingImage, paper_id=1, page_number=1)
        imgs = StagingImage.objects.all()
        self.assertEqual(res, [])

        # Add one collision
        paper2 = baker.make(StagingImage, paper_id=1, page_number=1)
        imgs = StagingImage.objects.all()
        res = ibs.find_internal_collisions(imgs)
        self.assertEqual(res, [(paper1, paper2)])

        # Add more collisions
        paper3 = baker.make(StagingImage, paper_id=1, page_number=1)
        paper4 = baker.make(StagingImage, paper_id=2, page_number=1)
        paper5 = baker.make(StagingImage, paper_id=2, page_number=1)
        baker.make(StagingImage, paper_id=2, page_number=4)

        imgs = StagingImage.objects.all()
        res = ibs.find_internal_collisions(imgs)
        self.assertEqual(
            set(res),
            set(
                [(paper1, paper2), (paper1, paper3), (paper2, paper3), (paper4, paper5)]
            ),
        )

    def test_find_external_collisions(self):
        """
        Test ImageBundleService.find_external_collisions()
        """

        ibs = ImageBundleService()
        res = ibs.find_external_collisions(StagingImage.objects.all())
        self.assertEqual(res, [])

        img1 = baker.make(StagingImage, paper_id=2, page_number=1)
        img2 = baker.make(StagingImage, paper_id=2, page_number=2)
        img3 = baker.make(StagingImage, paper_id=2, page_number=3)

        img4 = baker.make(Image)
        img5 = baker.make(Image)
        paper2 = baker.make(Paper, paper_number=2)
        paper3 = baker.make(Paper, paper_number=3)
        page1 = baker.make(BasePage, paper=paper3, page_number=1, image=img4)
        page2 = baker.make(BasePage, paper=paper3, page_number=2, image=img5)

        res = ibs.find_external_collisions(StagingImage.objects.all())
        self.assertEqual(res, [])

        img6 = baker.make(StagingImage, paper_id=3, page_number=1)
        res = ibs.find_external_collisions(StagingImage.objects.all())
        self.assertEqual(res, [(img6, img4)])
