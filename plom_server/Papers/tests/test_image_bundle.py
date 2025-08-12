# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.test import TestCase
from model_bakery import baker

from django.contrib.auth.models import User

from plom_server.Scan.models import StagingImage, StagingBundle, KnownStagingImage
from plom_server.Preparation.services import PapersPrinted
from plom_server.Preparation.models import StagingPQVMapping
from ..services import ImageBundleService, SpecificationService
from ..models import (
    Bundle,
    Image,
    Paper,
    DNMPage,
    FixedPage,
    QuestionPage,
    MobilePage,
)
from plom_server.Base.models import BaseImage


class ImageBundleTests(TestCase):
    """Tests for Papers.services.ImageBundelService."""

    def setUp(self) -> None:
        # make a spec and a paper
        spec_dict = {
            "idPage": 1,
            "numberOfVersions": 2,
            "numberOfPages": 5,
            "totalMarks": 10,
            "numberOfQuestions": 2,
            "name": "papers_demo",
            "longName": "Papers Test",
            "doNotMarkPages": [2, 5],
            "question": {
                "1": {"pages": [3], "mark": 5},
                "2": {"pages": [4], "mark": 5},
            },
        }
        SpecificationService._store_validated_spec(spec_dict)
        self.user: User = baker.make(User, username="testScanner")
        self.paper = baker.make(Paper, paper_number=1)
        self.page1 = baker.make(DNMPage, paper=self.paper, page_number=2)
        # make a staged bundle with one known image.
        self.staged_bundle = baker.make(StagingBundle, pdf_hash="abcde", user=self.user)
        self.staged_baseimage = baker.make(
            BaseImage,
            image_hash="abcdef",
        )
        self.staged_image = baker.make(
            StagingImage,
            bundle=self.staged_bundle,
            bundle_order=1,
            baseimage=self.staged_baseimage,
            rotation=90,
            image_type=StagingImage.KNOWN,
            _create_files=True,  # argument to tell baker to actually make the file
        )

        # supply p,p,v to this since we will need to cast it to a short-tpv code
        # and we don't (yet) fix maximum size of p,p,v in our models
        self.staged_known = baker.make(
            KnownStagingImage,
            staging_image=self.staged_image,
            paper_number=17,
            page_number=2,
            version=3,
        )

        # Set preparation as finished - since we are not actually
        # building the pdfs, we set 'ignore_dependencies'
        PapersPrinted.set_papers_printed(True, ignore_dependencies=True)

        return super().setUp()

    def test_create_bundle(self) -> None:
        """Test ImageBundlseService.create_bundle()."""
        n_bundles = Bundle.objects.all().count()
        self.assertEqual(n_bundles, 0)

        ibs = ImageBundleService()
        ibs.create_bundle("bundle1", "abcde")

        n_bundles = Bundle.objects.all().count()
        self.assertEqual(n_bundles, 1)

        with self.assertRaises(RuntimeError):
            ibs.create_bundle("bundle2", "abcde")

        n_bundles = Bundle.objects.all().count()
        self.assertEqual(n_bundles, 1)

    def test_all_staged_imgs_valid(self) -> None:
        """Test ImageBundleService.all_staged_imgs_valid().

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
                    StagingImage,
                    parsed_qr={"NW": "Not empty!"},
                    image_type=StagingImage.KNOWN,
                    bundle=self.staged_bundle,
                    _create_files=True,
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
        baker.make(
            StagingImage,
            image_type=StagingImage.UNREAD,
            bundle=self.staged_bundle,
            _create_files=True,
        )
        imgs = StagingImage.objects.all()
        self.assertFalse(ibs.all_staged_imgs_valid(imgs))

    def test_find_internal_collisions(self) -> None:
        """Test ImageBundleService.find_internal_collisions()."""
        ibs = ImageBundleService()
        imgs = StagingImage.objects.all()
        res = ibs.find_internal_collisions(imgs)
        self.assertEqual(res, [])

        img1 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
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
        img2 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
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
        img3 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
        baker.make(
            KnownStagingImage,
            staging_image=img3,
            paper_number=1,
            page_number=1,
            version=1,
        )

        img4 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
        baker.make(
            KnownStagingImage,
            staging_image=img4,
            paper_number=2,
            page_number=1,
            version=1,
        )

        img5 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
        baker.make(
            KnownStagingImage,
            staging_image=img5,
            paper_number=2,
            page_number=1,
            version=1,
        )

        img6 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
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

    def test_find_external_collisions(self) -> None:
        """Test ImageBundleService.find_external_collisions()."""
        ibs = ImageBundleService()
        res = ibs.find_external_collisions(StagingImage.objects.all())
        self.assertEqual(res, [])

        img1 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
        baker.make(KnownStagingImage, staging_image=img1, paper_number=2, page_number=1)

        img2 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
        baker.make(KnownStagingImage, staging_image=img2, paper_number=2, page_number=2)

        img3 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
        baker.make(KnownStagingImage, staging_image=img3, paper_number=2, page_number=3)

        img4 = baker.make(Image)
        img5 = baker.make(Image)

        baker.make(Paper, paper_number=2)
        paper3 = baker.make(Paper, paper_number=3)
        baker.make(FixedPage, paper=paper3, page_number=1, image=img4)
        baker.make(FixedPage, paper=paper3, page_number=2, image=img5)

        res = ibs.find_external_collisions(StagingImage.objects.all())
        self.assertEqual(res, [])

        st_img6 = baker.make(
            StagingImage,
            image_type=StagingImage.KNOWN,
            bundle=self.staged_bundle,
            _create_files=True,
        )
        baker.make(
            KnownStagingImage, staging_image=st_img6, paper_number=3, page_number=1
        )

        res = ibs.find_external_collisions(StagingImage.objects.all())

        self.assertEqual(res, [(st_img6, img4, 3, 1)])

    def test_perfect_bundle(self) -> None:
        """Test that upload_valid_bundle() works as intended with a valid staged bundle."""
        bundle = baker.make(StagingBundle, pdf_hash="abcdef", user=self.user)
        baker.make(StagingPQVMapping, paper_number=2, question=1, version=1)
        paper2 = baker.make(Paper, paper_number=2)
        paper3 = baker.make(Paper, paper_number=3)
        baker.make(QuestionPage, paper=paper2, page_number=1, question_index=1)
        baker.make(DNMPage, paper=paper3, page_number=2)

        bimg1 = baker.make(BaseImage, image_hash="ghijk", _create_files=True)
        img1 = baker.make(
            StagingImage,
            bundle=bundle,
            parsed_qr={"NW": "abcde"},
            baseimage=bimg1,
            image_type=StagingImage.KNOWN,
        )
        baker.make(
            KnownStagingImage,
            staging_image=img1,
            paper_number=2,
            page_number=1,
            version=1,
        )
        bimg2 = baker.make(BaseImage, image_hash="lmnop", _create_files=True)
        img2 = baker.make(
            StagingImage,
            bundle=bundle,
            parsed_qr={"NW": "abcde"},
            baseimage=bimg2,
            image_type=StagingImage.KNOWN,
        )
        baker.make(
            KnownStagingImage,
            staging_image=img2,
            paper_number=3,
            page_number=2,
            version=1,
        )

        ibs = ImageBundleService()
        ibs.upload_valid_bundle(bundle, self.user)

        self.assertEqual(Bundle.objects.all()[0].pdf_hash, bundle.pdf_hash)
        self.assertEqual(
            Image.objects.get(
                fixedpage__page_number=1, fixedpage__paper=paper2
            ).baseimage.image_hash,
            bimg1.image_hash,
        )


class ImageBundleReadyTests(TestCase):
    """Test 'ready' checking functions."""

    def setUp(self) -> None:
        # make a spec and a paper
        spec_dict = {
            "idPage": 1,
            "numberOfVersions": 2,
            "numberOfPages": 12,
            "totalMarks": 30,
            "numberOfQuestions": 3,
            "name": "papers_demo",
            "longName": "Papers Test",
            "doNotMarkPages": [2, 3],
            "question": {
                "1": {"pages": [4], "mark": 5},
                "2": {"pages": [5, 6], "mark": 5},
                "3": {"pages": [7, 8], "mark": 5},
                "4": {"pages": [9], "mark": 5},
                "5": {"pages": [10], "mark": 5},
            },
        }
        image_obj = baker.make(Image)
        SpecificationService._store_validated_spec(spec_dict)
        self.paper = baker.make(Paper, paper_number=1)
        self.page2 = baker.make(DNMPage, paper=self.paper, page_number=2)
        self.page3 = baker.make(DNMPage, paper=self.paper, page_number=3)
        self.page4 = baker.make(
            QuestionPage,
            paper=self.paper,
            page_number=4,
            question_index=1,
            image=image_obj,
        )
        self.page5 = baker.make(
            QuestionPage,
            paper=self.paper,
            page_number=5,
            question_index=2,
            image=image_obj,
        )
        self.page6 = baker.make(
            QuestionPage,
            paper=self.paper,
            page_number=6,
            question_index=2,
            image=image_obj,
        )
        self.page7 = baker.make(
            QuestionPage,
            paper=self.paper,
            page_number=7,
            question_index=3,
            image=image_obj,
        )
        self.page8 = baker.make(
            QuestionPage, paper=self.paper, page_number=8, question_index=3
        )
        self.page9 = baker.make(
            QuestionPage, paper=self.paper, page_number=9, question_index=4
        )
        self.extrapage1 = baker.make(
            MobilePage, paper=self.paper, question_index=4, image=image_obj
        )
        self.page10 = baker.make(
            QuestionPage, paper=self.paper, page_number=10, question_index=5
        )
        # questions that are ready: 1,2,4
        # questions that are not ready: 3,5
        return super().setUp()

    def test_are_paper_question_pairs_ready(self) -> None:
        ibs = ImageBundleService()
        pq_pairs = [
            (self.paper.paper_number, 1),
            (self.paper.paper_number, 2),
            (self.paper.paper_number, 3),
            (self.paper.paper_number, 4),
            (self.paper.paper_number, 5),
        ]
        pair_ready = ibs.are_paper_question_pairs_ready(pq_pairs)
        self.assertTrue(pair_ready[(self.paper.paper_number, 1)])
        self.assertTrue(pair_ready[(self.paper.paper_number, 2)])
        self.assertFalse(pair_ready[(self.paper.paper_number, 3)])
        self.assertTrue(pair_ready[(self.paper.paper_number, 4)])
        self.assertFalse(pair_ready[(self.paper.paper_number, 5)])

    def test__get_ready_paper_question_pairs(self) -> None:
        ibs = ImageBundleService()
        ready_pairs = [
            (self.paper.paper_number, 1),
            (self.paper.paper_number, 2),
            (self.paper.paper_number, 4),
        ]
        ready_pairs = sorted(ready_pairs)
        fetched_pairs = sorted(ibs._get_ready_paper_question_pairs())
        self.assertTrue(fetched_pairs == ready_pairs)

        # Q3 has one fixed page present and one missing, i.e. not ready
        # adding a mobilepage shouldn't cause Q3 to be ready
        baker.make(MobilePage, paper=self.paper, question_index=3)
        fetched_pairs = sorted(ibs._get_ready_paper_question_pairs())
        self.assertTrue(fetched_pairs == ready_pairs)

        # check mobile DNM pages aren't considered 'ready'
        baker.make(MobilePage, paper=self.paper, question_index=MobilePage.DNM_qidx)
        fetched_pairs = sorted(ibs._get_ready_paper_question_pairs())
        self.assertTrue(fetched_pairs == ready_pairs)
