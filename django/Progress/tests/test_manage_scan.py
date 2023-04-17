# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

from django.test import TestCase
from django.conf import settings
from model_bakery import baker
from unittest import skip


from Papers.models import Image, FixedPage, MobilePage, Bundle, Paper
from Scan.models import StagingImage, StagingBundle

from Progress.services import ManageScanService


class ManageScanTests(TestCase):
    """
    Tests for Progress.services.ManageScanService()
    """

    def setUp(self):
        self.bundle = baker.make(
            Bundle,
            hash="qwerty",
        )
        # make 10 papers, first 5 with fixed-page images, the next 5 without.
        # give papers 9 and 10 three mobile pages each (questions 1, 2, 3).
        # then make another 10 unused papers
        ord = 0
        # make the 5 complete papers
        for paper_number in range(1, 6):
            paper = baker.make(Paper, paper_number=paper_number)
            for pg in range(1, 7):
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(FixedPage, paper=paper, image=img, version=1, page_number=pg)
        # make 1 paper with 2 pages with images and 4 without (ie an incomplete paper)
        paper = baker.make(Paper, paper_number=6)
        for pg in range(1, 3):
            ord += 1
            img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
            baker.make(FixedPage, paper=paper, image=img, version=1, page_number=pg)
        for pg in range(3, 7):
            baker.make(FixedPage, paper=paper, image=None, version=1, page_number=pg)

        # make another 2 unused papers - no images at all
        for paper_number in range(7, 9):
            paper = baker.make(Paper, paper_number=paper_number)
            for pg in range(1, 7):
                baker.make(
                    FixedPage, paper=paper, image=None, version=1, page_number=pg
                )

        # make 2 papers with 3 mobile pages and all fixed pages unscanned
        for paper_number in range(9, 11):
            paper = baker.make(Paper, paper_number=paper_number)
            for pg in range(1, 7):
                baker.make(
                    FixedPage, paper=paper, image=None, version=1, page_number=pg
                )
            for qn in range(1, 4):
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(MobilePage, paper=paper, question_number=qn, image=img)

        return super().setUp()

    def test_counts(self):
        mss = ManageScanService()
        print(mss.get_total_test_papers())
        assert mss.get_total_test_papers() == 10
        assert mss.get_total_fixed_pages() == 10 * 6
        assert mss.get_total_mobile_pages() == 3 * 2
        assert mss.get_number_of_scanned_pages() == 5 * 6 + 1 * 2 + 2 * 3
        assert mss.get_number_unused_test_papers() == 2
        assert mss.get_number_completed_test_papers() == 5 + 2
        assert mss.get_number_incomplete_test_papers() == 1

    def test_get_all_unused_test_papers(self):
        mss = ManageScanService()
        assert mss.get_all_unused_test_papers() == [7, 8]

    def test_get_all_incomplete_test_papers(self):
        mss = ManageScanService()
        mss_incomplete = mss.get_all_incomplete_test_papers()
        # paper 6 is incomplete - should return dict of the form
        #
        # {6:[
        # {'type': 'fixed', 'page_number': 1, 'img_pk': 63}, {'type':
        # 'fixed', 'page_number': 2, 'img_pk': 64}, {'type':
        # 'missing', 'page_number': 3}, {'type': 'missing',
        # 'page_number': 4}, {'type': 'missing', 'page_number': 5},
        # {'type': 'missing', 'page_number': 6}
        # ]}

        assert 6 in mss_incomplete
        # it is missing pages 3,4,5,6, but has fixed pages 1,2 - the img_pk of those we can ignore.
        pg_data = mss_incomplete[6]
        assert len(pg_data) == 6
        for pg in [1, 2]:
            assert pg_data[pg - 1]["type"] == "fixed"
            assert pg_data[pg - 1]["page_number"] == pg
            assert (
                "img_pk" in pg_data[pg - 1]
            )  # not testing the actual value of image_pk
        for pg in range(3, 7):
            assert pg_data[pg - 1] == {"type": "missing", "page_number": pg}

    def test_get_all_completed_test_papers(self):
        mss = ManageScanService()
        mss_complete = mss.get_all_completed_test_papers()
        # should return a dict of papers and their pages
        # papers 1,2,3,4,5 = should have all 6 fixed pages - returned in page-number order
        # papers 9,10 should have 3 mobile pages (one each for q 1,2,3) - returned in question-number order
        assert len(mss_complete) == 7
        for pn in [1, 2, 3, 4, 5]:
            assert pn in mss_complete
            assert len(mss_complete[pn]) == 6
            page_data = mss_complete[pn]
            for pg in range(1, 7):
                self.assertEqual(page_data[pg - 1]["type"], "fixed")
                self.assertEqual(page_data[pg - 1]["page_number"], pg)
                assert (
                    "img_pk" in page_data[pg - 1]
                )  # not testing the actual value of image_pk

        for pn in [9, 10]:
            assert pn in mss_complete
            page_data = mss_complete[pn]
            for qn in range(1, 4):
                self.assertEqual(page_data[qn - 1]["type"], "mobile")
                self.assertEqual(page_data[qn - 1]["question_number"], qn)
                assert (
                    "img_pk" in page_data[qn - 1]
                )  # not testing the actual value of image_pk
