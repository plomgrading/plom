# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.test import TestCase
from django.contrib.auth.models import User
from model_bakery import baker

from plom_server.Papers.models import (
    Image,
    FixedPage,
    MobilePage,
    Paper,
    DNMPage,
    IDPage,
    QuestionPage,
    DiscardPage,
)
from ..services import ManageDiscardService


class ManageScanTests(TestCase):
    """Tests for Progress.services.ManageScanService."""

    def setUp(self) -> None:
        self.user0: User = baker.make(User, username="user0")
        self.paper1 = baker.make(Paper, paper_number=1)

        return super().setUp()

    def test_discard_idpage(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        id1 = baker.make(IDPage, paper=self.paper1, page_number=1, image=img1)

        mds.discard_pushed_fixed_page(self.user0, id1.pk, dry_run=True)
        mds.discard_pushed_fixed_page(self.user0, id1.pk, dry_run=False)

    def test_discard_dnm(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        dnm1 = baker.make(DNMPage, paper=self.paper1, page_number=2, image=img1)

        mds.discard_pushed_fixed_page(self.user0, dnm1.pk, dry_run=True)
        mds.discard_pushed_fixed_page(self.user0, dnm1.pk, dry_run=False)

    def test_discard_questionpage(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        qp1 = baker.make(QuestionPage, paper=self.paper1, page_number=3, image=img1)

        mds.discard_pushed_fixed_page(self.user0, qp1.pk, dry_run=True)
        mds.discard_pushed_fixed_page(self.user0, qp1.pk, dry_run=False)

    def test_discard_fixedpage_exceptions(self) -> None:
        mds = ManageDiscardService()
        fp1 = baker.make(FixedPage, paper=self.paper1, page_number=1, image=None)
        img1 = baker.make(Image)
        fp2 = baker.make(FixedPage, paper=self.paper1, page_number=2, image=img1)
        # find the largest pk and increase by 1 to get a PK that is not in the table
        pk_not_there = FixedPage.objects.latest("pk").pk + 1
        self.assertRaises(
            ValueError,
            mds.discard_pushed_fixed_page,
            self.user0,
            pk_not_there,
            dry_run=False,
        )
        self.assertRaises(
            ValueError, mds.discard_pushed_fixed_page, self.user0, fp1.pk, dry_run=False
        )
        self.assertRaises(
            ValueError, mds.discard_pushed_fixed_page, self.user0, fp2.pk, dry_run=False
        )

    def test_discard_mobile_page(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        baker.make(QuestionPage, paper=self.paper1, page_number=2, question_index=1)
        baker.make(QuestionPage, paper=self.paper1, page_number=2, question_index=2)
        mp1 = baker.make(MobilePage, paper=self.paper1, question_index=1, image=img1)
        mp2 = baker.make(MobilePage, paper=self.paper1, question_index=2, image=img1)
        pk_not_there = MobilePage.objects.latest("pk").pk + 1

        mds.discard_pushed_mobile_page(self.user0, mp1.pk, dry_run=True)
        mds.discard_pushed_mobile_page(self.user0, mp2.pk, dry_run=False)

        self.assertRaises(
            ValueError,
            mds.discard_pushed_mobile_page,
            self.user0,
            pk_not_there,
            dry_run=False,
        )

    def test_discard_image_from_pk(self) -> None:
        mds = ManageDiscardService()
        baker.make(FixedPage, paper=self.paper1, page_number=1, image=None)
        img1 = baker.make(Image)
        baker.make(FixedPage, paper=self.paper1, page_number=2, image=img1)
        pk_not_there = Image.objects.latest("pk").pk + 1
        # test when no such image
        self.assertRaises(
            ValueError, mds.discard_pushed_image_from_pk, self.user0, pk_not_there
        )
        # test when fixed page is not dnm, id or question page
        self.assertRaises(
            ValueError, mds.discard_pushed_image_from_pk, self.user0, img1.pk
        )

        # test when fixed page is an dnm page
        img2 = baker.make(Image)
        baker.make(DNMPage, paper=self.paper1, page_number=3, image=img2)
        mds.discard_pushed_image_from_pk(self.user0, img2.pk)
        # test when mobile page (need an associate question page)
        img3 = baker.make(Image)
        baker.make(QuestionPage, paper=self.paper1, page_number=4, question_index=1)
        baker.make(MobilePage, paper=self.paper1, question_index=1, image=img3)
        mds.discard_pushed_image_from_pk(self.user0, img3.pk)
        # test when discard page (no action required)
        img4 = baker.make(Image)

        baker.make(DiscardPage, image=img4)
        mds.discard_pushed_image_from_pk(self.user0, img4.pk)

    def test_reassign_discard_page_to_mobile(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        disc1 = baker.make(DiscardPage, image=img1)

        baker.make(
            QuestionPage,
            paper=self.paper1,
            page_number=2,
            question_index=1,
            image=None,
        )
        baker.make(
            QuestionPage,
            paper=self.paper1,
            page_number=3,
            question_index=2,
            image=None,
        )

        pk_not_there = DiscardPage.objects.latest("pk").pk + 1
        self.assertRaises(
            ValueError,
            mds._assign_discard_page_to_mobile_page,
            pk_not_there,
            1,
            [1],
        )
        mds._assign_discard_page_to_mobile_page(
            disc1.pk,
            1,
            [1, 2],
        )

    def test_reassign_discard_page_to_mobile_dnm(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        disc1 = baker.make(DiscardPage, image=img1)

        baker.make(
            QuestionPage,
            paper=self.paper1,
            page_number=2,
            question_index=1,
            image=None,
        )
        # [] means dnm
        mds._assign_discard_page_to_mobile_page(
            disc1.pk,
            1,
            [],
        )
        # ensure it was set properly
        mp = MobilePage.objects.filter(paper__paper_number=1).get()
        self.assertEqual(mp.question_index, MobilePage.DNM_qidx)

    def test_reassign_discard_to_fixed(self) -> None:
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        img2 = baker.make(Image)
        img3 = baker.make(Image)
        img4 = baker.make(Image)
        disc1 = baker.make(DiscardPage, image=img1)
        disc2 = baker.make(DiscardPage, image=img2)
        disc3 = baker.make(DiscardPage, image=img3)
        disc4 = baker.make(DiscardPage, image=img4)

        img0 = baker.make(Image)
        baker.make(
            IDPage,
            paper=self.paper1,
            page_number=1,
            image=None,
        )
        baker.make(
            QuestionPage,
            paper=self.paper1,
            page_number=2,
            question_index=1,
            image=img0,
        )
        baker.make(
            QuestionPage,
            paper=self.paper1,
            page_number=3,
            question_index=2,
            image=None,
        )
        baker.make(
            DNMPage,
            paper=self.paper1,
            page_number=4,
            image=None,
        )
        baker.make(FixedPage, paper=self.paper1, page_number=5, image=None)

        pk_not_there = DiscardPage.objects.latest("pk").pk + 1
        # try with non-existent image pk
        self.assertRaises(
            ValueError,
            mds.assign_discard_page_to_fixed_page,
            self.user0,
            pk_not_there,
            1,
            1,
        )
        # try to assign to page which already has an image
        self.assertRaises(
            ValueError,
            mds.assign_discard_page_to_fixed_page,
            self.user0,
            disc1.pk,
            1,
            2,
        )
        # now assign to a question page
        mds.assign_discard_page_to_fixed_page(
            self.user0,
            disc1.pk,
            1,
            3,
        )
        # and an ID-page
        mds.assign_discard_page_to_fixed_page(self.user0, disc2.pk, 1, 1)
        # and a DNM-page
        mds.assign_discard_page_to_fixed_page(self.user0, disc3.pk, 1, 4)
        # and this should raise an exception since the fixed page is not a Q,ID or DNM-page
        self.assertRaises(
            RuntimeError,
            mds.assign_discard_page_to_fixed_page,
            self.user0,
            disc4.pk,
            1,
            5,
        )

    def test_some_reassign_exceptions(self) -> None:
        mds = ManageDiscardService()
        # there are no discard pages, so can choose pk = 17 and it won't be there.
        pk_not_there = 17
        # test non-existent discardpage
        self.assertRaises(
            ValueError,
            mds._assign_discard_to_fixed_page,
            self.user0,
            pk_not_there,
            1,
            1,
        )
        self.assertRaises(
            ValueError,
            mds._assign_discard_page_to_mobile_page,
            pk_not_there,
            1,
            1,
        )
        dp1 = baker.make(DiscardPage)
        # test non-existent paper
        paper_not_there = Paper.objects.latest("paper_number").paper_number + 1
        self.assertRaises(
            ValueError,
            mds._assign_discard_to_fixed_page,
            self.user0,
            dp1.pk,
            paper_not_there,
            1,
        )
        self.assertRaises(
            ValueError,
            mds._assign_discard_page_to_mobile_page,
            dp1.pk,
            paper_not_there,
            1,
        )
        # test non-existent fixed page.
        # there are no fixed pages, so can just pick 1
        self.assertRaises(
            ValueError, mds._assign_discard_to_fixed_page, self.user0, dp1.pk, 1, 1
        )
