# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Andrew Rechnitzer

from django.test import TestCase
from django.conf import settings
from model_bakery import baker

from Papers.services import ImageBundleService
from Papers.models import (
    Bundle,
    Image,
    Paper,
    Specification,
    DNMPage,
    BasePage,
    QuestionPage,
)
from Scan.models import StagingImage, StagingBundle, KnownStagingImage


class ImageBundleTests(TestCase):
    """
    Tests for Papers.services.ImageBundelService
    """

    def setUp(self):
        # make a spec and a paper
        self.spec = baker.make(Specification)
        self.paper = baker.make(Paper, paper_number=1)
        self.page1 = baker.make(DNMPage, paper=self.paper, page_number=2)
        # make a staged bundle with one known image.
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
        If there are one or more images that are not "known" return False.
        Otherwise, return True.
        """

        ibs = ImageBundleService()
        imgs = StagingImage.objects.all()
        self.assertTrue(ibs.all_staged_imgs_valid(imgs))

        # make some known_pages
        for paper_num in range(2):
            for page_num in range(5):
                X = baker.make(
                    StagingImage, parsed_qr={"NW": "Not empty!"}, image_type="known"
                )
                baker.make(
                    KnownStagingImage,
                    staging_image=X,
                    paper_number=paper_num,
                    page_number=page_num,
                )
        imgs = StagingImage.objects.all()
        self.assertTrue(ibs.all_staged_imgs_valid(imgs))
        # add in an unread page
        baker.make(StagingImage, image_type="unread")
        imgs = StagingImage.objects.all()
        self.assertFalse(ibs.all_staged_imgs_valid(imgs))

    def test_find_internal_collisions(self):
        """
        Test ImageBundleService.find_internal_collisions()
        """

        ibs = ImageBundleService()
        imgs = StagingImage.objects.all()
        res = ibs.find_internal_collisions(imgs)
        self.assertEqual(res, [])

        img1 = baker.make(StagingImage, image_type="known")
        baker.make(
            KnownStagingImage,
            staging_image=img1,
            paper_number=1,
            page_number=1,
            version=1,
        )
        imgs = StagingImage.objects.all()
        self.assertEqual(res, [])

        # Add one collision
        img2 = baker.make(StagingImage, image_type="known")
        baker.make(
            KnownStagingImage,
            staging_image=img2,
            paper_number=1,
            page_number=1,
            version=1,
        )
        imgs = StagingImage.objects.all()
        res = ibs.find_internal_collisions(imgs)
        self.assertEqual(res, [[img1.pk, img2.pk]])

        # Add more collisions
        img3 = baker.make(StagingImage, image_type="known")
        baker.make(
            KnownStagingImage,
            staging_image=img3,
            paper_number=1,
            page_number=1,
            version=1,
        )

        img4 = baker.make(StagingImage, image_type="known")
        baker.make(
            KnownStagingImage,
            staging_image=img4,
            paper_number=2,
            page_number=1,
            version=1,
        )

        img5 = baker.make(StagingImage, image_type="known")
        baker.make(
            KnownStagingImage,
            staging_image=img5,
            paper_number=2,
            page_number=1,
            version=1,
        )

        img6 = baker.make(StagingImage, image_type="known")
        baker.make(
            KnownStagingImage,
            staging_image=img6,
            paper_number=2,
            page_number=1,
            version=1,
        )

        imgs = StagingImage.objects.all()
        res = ibs.find_internal_collisions(imgs)
        set_res = set([frozenset(X) for X in res])
        # Make lists into sets in order to compare in an unordered-way.
        # need to use "frozenset" because python does not like sets of sets.
        self.assertEqual(
            set_res,
            set(
                [
                    frozenset([img1.pk, img2.pk, img3.pk]),
                    frozenset([img4.pk, img5.pk, img6.pk]),
                ]
            ),
        )

    def test_find_external_collisions(self):
        """
        Test ImageBundleService.find_external_collisions()
        """

        ibs = ImageBundleService()
        res = ibs.find_external_collisions(StagingImage.objects.all())
        self.assertEqual(res, [])

        img1 = baker.make(StagingImage)
        baker.make(KnownStagingImage, staging_image=img1, paper_number=2, page_number=1)

        img2 = baker.make(StagingImage)
        baker.make(KnownStagingImage, staging_image=img2, paper_number=2, page_number=2)

        img3 = baker.make(StagingImage)
        baker.make(KnownStagingImage, staging_image=img3, paper_number=2, page_number=3)

        img4 = baker.make(Image)
        img5 = baker.make(Image)

        baker.make(Paper, paper_number=2)
        paper3 = baker.make(Paper, paper_number=3)
        baker.make(BasePage, paper=paper3, page_number=1, image=img4)
        baker.make(BasePage, paper=paper3, page_number=2, image=img5)

        res = ibs.find_external_collisions(StagingImage.objects.all())
        self.assertEqual(res, [])

        st_img6 = baker.make(StagingImage)
        baker.make(
            KnownStagingImage, staging_image=st_img6, paper_number=3, page_number=1
        )

        res = ibs.find_external_collisions(StagingImage.objects.all())

        self.assertEqual(res, [(st_img6, img4, 3, 1)])

    def test_perfect_bundle(self):
        """
        Test that upload_valid_bundle() works as intended with a valid
        staged bundle.
        """

        bundle = baker.make(StagingBundle, pdf_hash="abcdef")

        paper2 = baker.make(Paper, paper_number=2)
        paper3 = baker.make(Paper, paper_number=3)
        baker.make(QuestionPage, paper=paper2, page_number=1)
        baker.make(DNMPage, paper=paper3, page_number=2)

        img1 = baker.make(
            StagingImage,
            bundle=bundle,
            parsed_qr={"NW": "abcde"},
            image_hash="ghijk",
            image_type="known",
        )
        baker.make(
            KnownStagingImage,
            staging_image=img1,
            paper_number=2,
            page_number=1,
            version=1,
        )
        img2 = baker.make(
            StagingImage,
            bundle=bundle,
            parsed_qr={"NW": "abcde"},
            image_type="known",
        )
        baker.make(
            KnownStagingImage,
            staging_image=img2,
            paper_number=3,
            page_number=2,
            version=1,
        )

        ibs = ImageBundleService()
        ibs.upload_valid_bundle(bundle)

        self.assertEqual(Bundle.objects.all()[0].hash, bundle.pdf_hash)
        self.assertEqual(
            Image.objects.get(basepage__page_number=1, basepage__paper=paper2).hash,
            img1.image_hash,
        )
