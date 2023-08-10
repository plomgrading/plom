# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User

from model_bakery import baker

from Papers.models import (
    Image,
    FixedPage,
    MobilePage,
    Bundle,
    Paper,
    DNMPage,
    IDPage,
    QuestionPage,
)

from Progress.services import ManageDiscardService


class ManageScanTests(TestCase):
    """
    Tests for Progress.services.ManageScanService()
    """

    def setUp(self):
        self.user0 = baker.make(User, username="user0")
        self.paper1 = baker.make(Paper, paper_number=1)

        return super().setUp()

    def test_discard_idpage(self):
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        id1 = baker.make(IDPage, paper=self.paper1, page_number=1, image=img1)

        mds.discard_pushed_fixed_page(self.user0, id1.pk, dry_run=True)
        mds.discard_pushed_fixed_page(self.user0, id1.pk, dry_run=False)

    def test_discard_dnm(self):
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        dnm1 = baker.make(DNMPage, paper=self.paper1, page_number=2, image=img1)

        mds.discard_pushed_fixed_page(self.user0, dnm1.pk, dry_run=True)
        mds.discard_pushed_fixed_page(self.user0, dnm1.pk, dry_run=False)

    def test_discard_questionpage(self):
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        qp1 = baker.make(QuestionPage, paper=self.paper1, page_number=3, image=img1)

        mds.discard_pushed_fixed_page(self.user0, qp1.pk, dry_run=True)
        mds.discard_pushed_fixed_page(self.user0, qp1.pk, dry_run=False)

    def test_discard_fixedpage_exceptions(self):
        mds = ManageDiscardService()
        fp1 = baker.make(FixedPage, paper=self.paper1, page_number=1, image=None)
        img1 = baker.make(Image)
        fp2 = baker.make(FixedPage, paper=self.paper1, page_number=2, image=img1)
        self.assertRaises(
            ValueError, mds.discard_pushed_fixed_page, self.user0, 17, dry_run=False
        )
        self.assertRaises(
            ValueError, mds.discard_pushed_fixed_page, self.user0, fp1.pk, dry_run=False
        )
        self.assertRaises(
            ValueError, mds.discard_pushed_fixed_page, self.user0, fp2.pk, dry_run=False
        )

    def test_discard_mobile_page(self):
        mds = ManageDiscardService()

        img1 = baker.make(Image)
        baker.make(QuestionPage, paper=self.paper1, page_number=2, question_number=1)
        baker.make(QuestionPage, paper=self.paper1, page_number=2, question_number=2)
        mp1 = baker.make(MobilePage, paper=self.paper1, question_number=1, image=img1)
        mp1 = baker.make(MobilePage, paper=self.paper1, question_number=2, image=img1)

        mds.discard_pushed_mobile_page(self.user0, mp1.pk, dry_run=True)
        mds.discard_pushed_mobile_page(self.user0, mp1.pk, dry_run=False)

        self.assertRaises(
            ValueError, mds.discard_pushed_mobile_page, self.user0, 17, dry_run=False
        )
