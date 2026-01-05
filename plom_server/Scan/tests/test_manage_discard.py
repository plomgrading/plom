# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.test import TestCase
from django.contrib.auth.models import User
from model_bakery import baker

from plom_server.TestingSupport.utils import config_test
from plom_server.Identify.models import PaperIDTask
from plom_server.Mark.models import MarkingTask
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


class TestManageDiscard(TestCase):
    """Tests for Scan.services.ManageDiscardService."""

    mds = ManageDiscardService()

    @config_test(
        {
            "test_spec": "demo",
            "test_sources": "demo",
            "classlist": "demo",
            "num_to_produce": 1,
            "auto_init_tasks": True,
        }
    )
    def setUp(self) -> None:
        self.user0: User = baker.make(User, username="user0")
        self.paper1 = Paper.objects.get(paper_number=1)

        tasks = MarkingTask.objects.all()
        papers = Paper.objects.all()
        for paper in papers[0:6]:
            for j in range(1, 2):
                task = tasks.get(paper=paper, question_index=j)
                task.status = MarkingTask.COMPLETE
                task.save()

        return super().setUp()

    def test_discard_idpage(self) -> None:
        img1 = baker.make(Image)
        id1 = baker.make(IDPage, paper=self.paper1, page_number=1, image=img1)

        self.mds.discard_pushed_fixed_page(self.user0, id1.pk, dry_run=True)
        self.mds.discard_pushed_fixed_page(self.user0, id1.pk, dry_run=False)

    def test_discard_dnm(self) -> None:
        img1 = baker.make(Image)
        dnm1 = baker.make(DNMPage, paper=self.paper1, page_number=2, image=img1)

        self.mds.discard_pushed_fixed_page(self.user0, dnm1.pk, dry_run=True)
        self.mds.discard_pushed_fixed_page(self.user0, dnm1.pk, dry_run=False)

    def test_discard_questionpage(self) -> None:
        img1 = baker.make(Image)
        qp1 = baker.make(
            QuestionPage, paper=self.paper1, page_number=3, image=img1, question_index=1
        )

        self.mds.discard_pushed_fixed_page(self.user0, qp1.pk, dry_run=True)
        self.mds.discard_pushed_fixed_page(self.user0, qp1.pk, dry_run=False)

    def test_discard_fixedpage_exceptions(self) -> None:
        fp1 = baker.make(FixedPage, paper=self.paper1, page_number=1, image=None)
        img1 = baker.make(Image)
        fp2 = baker.make(FixedPage, paper=self.paper1, page_number=2, image=img1)
        # find the largest pk and increase by 1 to get a PK that is not in the table
        pk_not_there = FixedPage.objects.latest("pk").pk + 1
        self.assertRaises(
            ValueError,
            self.mds.discard_pushed_fixed_page,
            self.user0,
            pk_not_there,
            dry_run=False,
        )
        self.assertRaises(
            ValueError,
            self.mds.discard_pushed_fixed_page,
            self.user0,
            fp1.pk,
            dry_run=False,
        )
        self.assertRaises(
            ValueError,
            self.mds.discard_pushed_fixed_page,
            self.user0,
            fp2.pk,
            dry_run=False,
        )

    def test_discard_mobile_page(self) -> None:
        """Test discard_mobile_page."""
        img1 = baker.make(Image)
        baker.make(MobilePage, paper=self.paper1, question_index=1, image=img1)
        pk_not_there = MobilePage.objects.latest("pk").pk + 1

        self.assertRaises(
            ValueError,
            self.mds.discard_pushed_mobile_page,
            self.user0,
            pk_not_there,
            dry_run=False,
        )

    def test__discard_mobile_page(self) -> None:
        """Test _discard_mobile_page.

        `refresh_from_db` is sort of like 'assert_exists'.
        """
        img1 = baker.make(Image)
        mp1 = baker.make(MobilePage, paper=self.paper1, question_index=1, image=img1)
        mp2 = baker.make(MobilePage, paper=self.paper1, question_index=2, image=img1)
        task1 = MarkingTask.objects.get(paper=self.paper1, question_index=1)
        assert task1.status == MarkingTask.COMPLETE

        # this should:
        # (1) out of date the associated marking task
        # (2) delete the mobile page
        # (3) not create a Discard page because mp2 still references img1
        self.mds._discard_mobile_page(self.user0, mp1)
        task1.refresh_from_db()
        assert task1.status == MarkingTask.OUT_OF_DATE
        with self.assertRaisesRegex(MobilePage.DoesNotExist, "does not exist"):
            mp1.refresh_from_db()
        assert not DiscardPage.objects.filter(image=img1).exists()

        # this should create the DiscardPage, because no MobilePage references img1
        self.mds._discard_mobile_page(self.user0, mp2)
        with self.assertRaisesRegex(MobilePage.DoesNotExist, "does not exist"):
            mp2.refresh_from_db()
        assert DiscardPage.objects.filter(image=img1).exists()

    def test__discard_mobile_page_cascade(self) -> None:
        """Test _discard_mobile_page 'cascade' kwarg.

        `refresh_from_db` is sort of like 'assert_exists'.
        """
        img1 = baker.make(Image)
        mp1 = baker.make(MobilePage, paper=self.paper1, question_index=1, image=img1)
        mp2 = baker.make(MobilePage, paper=self.paper1, question_index=2, image=img1)
        mp3 = baker.make(MobilePage, paper=self.paper1, question_index=3, image=img1)

        # this should only delete the specified MobilePage (default behaviour)
        self.mds._discard_mobile_page(self.user0, mp3, cascade=False)
        with self.assertRaisesRegex(MobilePage.DoesNotExist, "does not exist"):
            mp3.refresh_from_db()
        mp2.refresh_from_db()
        mp1.refresh_from_db()

        # this should delete all mobile pages referencing img1 (mp1, mp2)
        # and create a DiscardPage referencing img1
        self.mds._discard_mobile_page(self.user0, mp1, cascade=True)
        with self.assertRaisesRegex(MobilePage.DoesNotExist, "does not exist"):
            mp1.refresh_from_db()
        with self.assertRaisesRegex(MobilePage.DoesNotExist, "does not exist"):
            mp2.refresh_from_db()
        assert DiscardPage.objects.filter(image=img1).exists()

    def test_discard_image_from_pk(self) -> None:
        baker.make(FixedPage, paper=self.paper1, page_number=1, image=None)
        img1 = baker.make(Image)
        baker.make(FixedPage, paper=self.paper1, page_number=2, image=img1)
        pk_not_there = Image.objects.latest("pk").pk + 1
        # test when no such image
        self.assertRaises(
            ValueError, self.mds.discard_pushed_image_from_pk, self.user0, pk_not_there
        )
        # test when fixed page is not dnm, id or question page
        self.assertRaises(
            ValueError, self.mds.discard_pushed_image_from_pk, self.user0, img1.pk
        )

        # test when fixed page is an dnm page
        img2 = baker.make(Image)
        baker.make(DNMPage, paper=self.paper1, page_number=3, image=img2)
        self.mds.discard_pushed_image_from_pk(self.user0, img2.pk)
        # test when mobile page (need an associate question page)
        img3 = baker.make(Image)
        baker.make(QuestionPage, paper=self.paper1, page_number=4, question_index=1)
        baker.make(MobilePage, paper=self.paper1, question_index=1, image=img3)
        self.mds.discard_pushed_image_from_pk(self.user0, img3.pk)
        # test when discard page (no action required)
        img4 = baker.make(Image)

        baker.make(DiscardPage, image=img4)
        self.mds.discard_pushed_image_from_pk(self.user0, img4.pk)

    def test_reassign_discard_page_to_mobile(self) -> None:
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
            self.mds._assign_discard_page_to_mobile_page,
            pk_not_there,
            1,
            [1],
        )
        self.mds._assign_discard_page_to_mobile_page(
            disc1.pk,
            1,
            [1, 2],
        )

    def test_reassign_discard_page_to_mobile_dnm(self) -> None:
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
        self.mds._assign_discard_page_to_mobile_page(
            disc1.pk,
            1,
            [],
        )
        # ensure it was set properly
        mp = MobilePage.objects.filter(paper__paper_number=1).get()
        self.assertEqual(mp.question_index, MobilePage.DNM_qidx)

    def test_reassign_discard_to_fixed(self) -> None:
        img1 = baker.make(Image)
        img2 = baker.make(Image)
        img3 = baker.make(Image)
        img4 = baker.make(Image)
        disc1 = baker.make(DiscardPage, image=img1)
        disc2 = baker.make(DiscardPage, image=img2)
        disc3 = baker.make(DiscardPage, image=img3)
        disc4 = baker.make(DiscardPage, image=img4)

        img0 = baker.make(Image)
        qp3 = QuestionPage.objects.get(paper=self.paper1, page_number=3)
        qp3.image = img0
        qp3.save()
        baker.make(FixedPage, paper=self.paper1, page_number=7, image=None)

        pk_not_there = DiscardPage.objects.latest("pk").pk + 1
        # try with non-existent image pk
        self.assertRaises(
            ValueError,
            self.mds.assign_discard_page_to_fixed_page,
            self.user0,
            pk_not_there,
            1,
            1,
        )
        # try to assign to page which already has an image
        self.assertRaises(
            ValueError,
            self.mds.assign_discard_page_to_fixed_page,
            self.user0,
            disc1.pk,
            1,
            3,
        )
        # now assign to a question page
        self.mds.assign_discard_page_to_fixed_page(
            self.user0,
            disc1.pk,
            1,
            4,
        )
        # and an ID-page
        self.mds.assign_discard_page_to_fixed_page(self.user0, disc2.pk, 1, 1)
        # and a DNM-page
        self.mds.assign_discard_page_to_fixed_page(self.user0, disc3.pk, 1, 2)
        # and this should raise an exception since the fixed page is not a Q,ID or DNM-page
        self.assertRaises(
            RuntimeError,
            self.mds.assign_discard_page_to_fixed_page,
            self.user0,
            disc4.pk,
            1,
            7,
        )

    def test_some_reassign_exceptions(self) -> None:
        # there are no discard pages, so can choose pk = 17 and it won't be there.
        pk_not_there = 17
        page_not_there = 12000  # this is lazy, should check spec
        # test non-existent discardpage
        self.assertRaises(
            ValueError,
            self.mds.assign_discard_page_to_fixed_page,
            self.user0,
            pk_not_there,
            1,
            1,
        )
        self.assertRaises(
            ValueError,
            self.mds._assign_discard_page_to_mobile_page,
            pk_not_there,
            1,
            1,
        )
        dp1 = baker.make(DiscardPage)
        # test non-existent paper
        paper_not_there = Paper.objects.latest("paper_number").paper_number + 1
        self.assertRaises(
            ValueError,
            self.mds.assign_discard_page_to_fixed_page,
            self.user0,
            dp1.pk,
            paper_not_there,
            1,
        )
        self.assertRaises(
            ValueError,
            self.mds._assign_discard_page_to_mobile_page,
            dp1.pk,
            paper_not_there,
            1,
        )
        # test non-existent fixed page.
        # there are no fixed pages, so can just pick 1
        self.assertRaises(
            ValueError,
            self.mds.assign_discard_page_to_fixed_page,
            self.user0,
            dp1.pk,
            1,
            page_not_there,
        )

    def test_discard_whole_paper_by_number_standard(self) -> None:
        """Test discarding a whole paper."""
        img1 = baker.make(Image)
        img2 = baker.make(Image)
        img3 = baker.make(Image)
        img4 = baker.make(Image)
        img5 = baker.make(Image)
        img6 = baker.make(Image)
        img7 = baker.make(Image)
        img8 = baker.make(Image)
        images = [img1, img2, img3, img4, img5, img6, img7, img8]
        baker.make(MobilePage, paper=self.paper1, question_index=1, image=img7)
        baker.make(MobilePage, paper=self.paper1, question_index=2, image=img7)
        baker.make(MobilePage, paper=self.paper1, question_index=3, image=img8)
        fp1 = FixedPage.objects.get(paper=self.paper1, page_number=1)
        fp2 = FixedPage.objects.get(paper=self.paper1, page_number=2)
        fp3 = FixedPage.objects.get(paper=self.paper1, page_number=3)
        fp4 = FixedPage.objects.get(paper=self.paper1, page_number=4)
        fp5 = FixedPage.objects.get(paper=self.paper1, page_number=5)
        fp6 = FixedPage.objects.get(paper=self.paper1, page_number=6)
        for index, fp in enumerate([fp1, fp2, fp3, fp4, fp5, fp6]):
            fp.image = images[index]
            fp.save()

        idtask = PaperIDTask.objects.get(paper=self.paper1)
        idtask.status = PaperIDTask.COMPLETE
        idtask.save()

        marking_tasks = MarkingTask.objects.all().filter(paper=self.paper1)
        for mt in marking_tasks:
            mt.status = MarkingTask.COMPLETE
            mt.save()

        # this is for (4) below
        for img in images:
            assert not DiscardPage.objects.filter(image=img).exists()

        # we are checking:
        # (1) id task is invalidated
        # (2) marking tasks are invalidated
        # (3) Fixed pages don't have any images, MobilePages have been deleted
        # (4) a discard page is created for each distinct image in the original paper
        self.mds.discard_whole_paper_by_number(
            self.user0, self.paper1.paper_number, dry_run=False
        )

        # (1)
        idtask.refresh_from_db()
        assert idtask.status == PaperIDTask.OUT_OF_DATE, f"task status:{idtask.status}"

        # (2)
        marking_tasks = MarkingTask.objects.all().filter(paper=self.paper1)
        for mt in marking_tasks:
            assert mt.status == MarkingTask.OUT_OF_DATE

        # (3)
        for fp in [fp1, fp2, fp3, fp4, fp5, fp6]:
            fp.refresh_from_db()
            assert fp.image is None
        assert not MobilePage.objects.filter(paper=self.paper1).exists()

        # (4)
        for img in images:
            assert DiscardPage.objects.filter(image=img).exists()

    def test_discard_whole_paper_by_number_no_id(self) -> None:
        """Test discarding a whole paper without an id page."""
        img7 = baker.make(Image)
        img8 = baker.make(Image)
        baker.make(MobilePage, paper=self.paper1, question_index=1, image=img7)
        baker.make(MobilePage, paper=self.paper1, question_index=2, image=img7)
        baker.make(MobilePage, paper=self.paper1, question_index=3, image=img8)

        idtask = PaperIDTask.objects.get(paper=self.paper1)
        idtask.status = PaperIDTask.COMPLETE
        idtask.save()

        self.mds.discard_whole_paper_by_number(
            self.user0, self.paper1.paper_number, dry_run=False
        )

        # check that id task is invalidated
        idtask.refresh_from_db()
        assert idtask.status == PaperIDTask.OUT_OF_DATE, f"task status:{idtask.status}"
