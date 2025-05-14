# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.test import TestCase
from model_bakery import baker

from plom_server.Base.tests import config_test
from plom_server.Papers.models import Image, FixedPage, MobilePage, Bundle, Paper
from ..services import ManageScanService


class ManageScanServiceTests(TestCase):
    """Tests for Progress.services.ManageScanService."""

    @config_test({"test_spec": "demo"})
    def setUp(self):
        self.bundle = baker.make(
            Bundle,
            pdf_hash="qwerty",
        )
        # make 15 papers
        # * 1 has all fixed-page images  (6 scanned pages) and 1 mobile page for Q1.
        # * 1,2,3,4 with fixed-page images  (6*4 scanned pages)
        # * 6,7 = 2 scanned fixed pages, 4 unscanned = incomplete  (2*2 scanned pages)
        # * 8,9 = completely unscanned = unused
        # * 10,11 = 2 scanned fixed pages, 4 unscanned, 2 mobile pages = incomplete  (2*2 scanned, 2*2 mobile)
        # * 12,13,14,15 = three mobile pages each (questions 1, 2, 3). (3*2 mobile)
        ord = 0
        # make the 5 complete papers
        for paper_number in [1]:
            paper = baker.make(Paper, paper_number=paper_number)
            for pg in range(1, 7):
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(FixedPage, paper=paper, image=img, version=1, page_number=pg)
            for qn in [1]:
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(MobilePage, paper=paper, question_index=qn, image=img)
        # now make the other 4 papers, all fixed, but no mobile pages
        for paper_number in [2, 3, 4, 5]:
            paper = baker.make(Paper, paper_number=paper_number)
            for pg in range(1, 7):
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(FixedPage, paper=paper, image=img, version=1, page_number=pg)

        # make2 papers with 2 pages with images and 4 without (ie an incomplete paper)
        for paper_number in [6, 7]:
            paper = baker.make(Paper, paper_number=paper_number)
            for pg in range(1, 3):
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(FixedPage, paper=paper, image=img, version=1, page_number=pg)
            for pg in range(3, 7):
                baker.make(
                    FixedPage, paper=paper, image=None, version=1, page_number=pg
                )

        # make another 2 unused papers - no images at all
        for paper_number in [8, 9]:
            paper = baker.make(Paper, paper_number=paper_number)
            for pg in range(1, 7):
                baker.make(
                    FixedPage, paper=paper, image=None, version=1, page_number=pg
                )

        # make another 2 papers with 2 pages with images and 4 without (ie an incomplete paper), but 2 mobile pages (for q 1,2)
        for paper_number in [10, 11]:
            paper = baker.make(Paper, paper_number=paper_number)
            for pg in range(1, 3):
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(FixedPage, paper=paper, image=img, version=1, page_number=pg)
            for pg in range(3, 7):
                baker.make(
                    FixedPage, paper=paper, image=None, version=1, page_number=pg
                )
            for qn in range(1, 3):
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(MobilePage, paper=paper, question_index=qn, image=img)

        # make 4 papers with 3 mobile pages and all fixed pages unscanned
        for paper_number in [12, 13, 14, 15]:
            paper = baker.make(Paper, paper_number=paper_number)
            for pg in range(1, 7):
                baker.make(
                    FixedPage, paper=paper, image=None, version=1, page_number=pg
                )
            for qn in range(1, 4):
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(MobilePage, paper=paper, question_index=qn, image=img)

        return super().setUp()

    def test_counts(self) -> None:
        # make 15 papers
        # * 1 has all fixed-page images  (6 scanned pages) and 1 mobile page for Q1.
        # * 1,2,3,4 with fixed-page images  (6*4 scanned pages)
        # * 6,7 = 2 scanned fixed pages, 4 unscanned = incomplete  (2*2 scanned pages)
        # * 8,9 = completely unscanned = unused
        # * 10,11 = 2 scanned fixed pages, 4 unscanned, 2 mobile pages = incomplete  (2*2 scanned, 2*2 mobile)
        # * 12,13,14,15 = three mobile pages each (questions 1, 2, 3). (3*2 mobile)
        mss = ManageScanService()
        assert mss.get_total_papers() == 15
        assert mss.get_total_fixed_pages() == 15 * 6
        assert mss.get_total_mobile_pages() == 1 + 2 * 2 + 4 * 3
        assert (
            mss.get_number_of_scanned_pages()
            == 5 * 6 + 1 + 2 * 2 + 2 * 2 + 2 * 2 + 4 * 3
        )
        assert mss.get_number_unused_papers() == 2
        assert mss.get_number_completed_papers() == 5 + 4
        assert mss.get_number_incomplete_papers() == 2 + 2

    def test_get_all_used_and_unused_papers(self) -> None:
        unused = [8, 9]
        self.assertEqual(ManageScanService.get_all_unused_papers(), unused)
        used = [x for x in range(1, 16) if x not in unused]
        self.assertEqual(ManageScanService.get_all_used_papers(), used)

    def test_get_all_incomplete_papers(self) -> None:
        mss_incomplete = ManageScanService.get_all_incomplete_papers()
        # papers 6,7,10,11 is incomplete - should return dict of the form
        #
        # 6: {'fixed': [{'status': 'present', 'page_number': 1,
        # 'page_pk': 211, 'img_pk': 142}, {'status': 'present',
        # 'page_number': 2, 'page_pk': 212, 'img_pk': 143},
        # {'status': 'missing', 'page_number': 3, 'page_pk': 213,
        # 'kind': 'QuestionPage'}, {'status': 'missing',
        # 'page_number': 4, 'page_pk': 214, 'kind': 'QuestionPage'},
        # {'status': 'missing', 'page_number': 5, 'page_pk': 215,
        # 'kind': 'QuestionPage'}, {'status': 'missing',
        # 'page_number': 6, 'page_pk': 216, 'kind': 'QuestionPage'}],
        # 'mobile': []},

        assert len(mss_incomplete) == 4
        for pn in [6, 7]:
            assert 6 in mss_incomplete
            # it is missing pages 3,4,5,6, but has fixed pages 1,2 - the img_pk of those we can ignore.
            f_pg_data = mss_incomplete[pn]["fixed"]
            assert len(f_pg_data) == 6
            for pg in [1, 2]:
                assert f_pg_data[pg - 1]["status"] == "present"
                assert f_pg_data[pg - 1]["page_number"] == pg
                assert (
                    "img_pk" in f_pg_data[pg - 1]
                )  # not testing the actual value of image_pk
            for pg in range(3, 7):
                assert f_pg_data[pg - 1]["status"] == "missing"
                assert f_pg_data[pg - 1]["page_number"] == pg
                assert f_pg_data[pg - 1]["kind"] == "QuestionPage"
                # not testing value of page_pk
                assert "page_pk" in f_pg_data[pg - 1]
                # the image should be missing
                assert "img_pk" not in f_pg_data[pg - 1]
        for pn in [10, 11]:
            assert pn in mss_incomplete
            # it is missing pages 3,4,5,6, but has fixed pages 1,2 and mobile for q1,2- the img_pk of those we can ignore.
            f_pg_data = mss_incomplete[pn]["fixed"]
            m_pg_data = mss_incomplete[pn]["mobile"]
            assert len(f_pg_data) == 6
            assert len(m_pg_data) == 2
            for pg in [1, 2]:
                assert f_pg_data[pg - 1]["status"] == "present"
                assert f_pg_data[pg - 1]["page_number"] == pg
                assert (
                    "img_pk" in f_pg_data[pg - 1]
                )  # not testing the actual value of image_pk
            for pg in range(3, 7):
                assert f_pg_data[pg - 1]["status"] == "missing"
                assert f_pg_data[pg - 1]["page_number"] == pg
                assert f_pg_data[pg - 1]["kind"] == "QuestionPage"
                # not testing value of page_pk
                assert "page_pk" in f_pg_data[pg - 1]
                # the image should be missing
                assert "img_pk" not in f_pg_data[pg - 1]
            for pg in range(1, 3):
                assert (
                    m_pg_data[pg - 1]["question_idx"] == pg
                )  # 7th, 8th entries are q's 1,2.
                assert (
                    "img_pk" in m_pg_data[pg - 1]
                )  # not testing the actual value of image_pk

    def test_get_all_complete_papers(self) -> None:
        mss_complete = ManageScanService.get_all_complete_papers()
        # should return a dict of papers and their pages
        # paper 1 has 6 fixed and 1 mobile.
        # papers 2,3,4,5 = should have all 6 fixed pages - returned in page-number order
        # papers 12,13,14,15 should have 3 mobile pages (one each for q 1,2,3) - returned in question order
        assert len(mss_complete) == 9, f"mss_complete ({len(mss_complete)}) should be 9"

        for pn in [1]:
            assert pn in mss_complete
            assert len(mss_complete[pn]["fixed"]) == 6
            assert len(mss_complete[pn]["mobile"]) == 1
            f_page_data = mss_complete[pn]["fixed"]
            m_page_data = mss_complete[pn]["mobile"]
            for pg in range(1, 7):
                self.assertEqual(f_page_data[pg - 1]["page_number"], pg)
                assert (
                    "img_pk" in f_page_data[pg - 1]
                )  # not testing the actual value of image_pk

            for qn in [1]:  # is the 7th page of the test
                self.assertEqual(m_page_data[0]["question_idx"], qn)
                assert (
                    "img_pk" in m_page_data[qn - 1]
                )  # not testing the actual value of image_pk
        for pn in [2, 3, 4, 5]:
            assert pn in mss_complete
            assert len(mss_complete[pn]["fixed"]) == 6
            f_page_data = mss_complete[pn]["fixed"]
            for pg in range(1, 7):
                self.assertEqual(f_page_data[pg - 1]["page_number"], pg)
                assert (
                    "img_pk" in f_page_data[pg - 1]
                )  # not testing the actual value of image_pk

        for pn in [12, 13, 14, 15]:
            assert pn in mss_complete
            m_page_data = mss_complete[pn]["mobile"]
            for qn in range(1, 4):
                self.assertEqual(m_page_data[qn - 1]["question_idx"], qn)
                assert (
                    "img_pk" in m_page_data[qn - 1]
                )  # not testing the actual value of image_pk

    def test_is_paper_completely_scanned(self) -> None:
        """Test whether we can tell if a paper is scanned."""
        # papers 6, 7, 10, 11 are incomplete

        mss = ManageScanService()
        assert mss.is_paper_completely_scanned(1)
        assert mss.is_paper_completely_scanned(12)
        assert not mss.is_paper_completely_scanned(6)
