# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Aidan Murphy

from django.test import TestCase
from model_bakery import baker

from plom_server.Base.tests import config_test
from plom_server.Papers.models import Paper, Image, FixedPage, MobilePage, Bundle
from plom_server.Mark.models import MarkingTask
from ..services import StudentMarkService

NUM_PAPERS = 10


class TestStudentMarkService(TestCase):
    """Tests for Finish.service.StudentMarkService."""

    sms = StudentMarkService

    @config_test(
        {
            "test_spec": "demo",
            "test_sources": "demo",
            "classlist": "demo",
            "num_to_produce": NUM_PAPERS,
            "auto_init_tasks": True,
        }
    )
    def setUp(self):
        return

    def test_is_paper_marked(self) -> None:
        """Are all questions in a paper marked."""
        # papers 1-5 are "marked"
        # papers 6-8 are "unmarked"
        # papers 9, 10 are "unmarked"
        tasks = MarkingTask.objects.all()
        papers = Paper.objects.all()
        for paper in papers[0:6]:
            for j in range(1, 4):
                task = tasks.get(paper=paper, question_index=j)
                task.status = MarkingTask.COMPLETE
                task.save()
        for paper in papers[6:9]:
            for j in range(1, 3):
                task = tasks.get(paper=paper, question_index=j)
                task.status = MarkingTask.COMPLETE
                task.save()

        for i in range(0, 6):
            assert self.sms.is_paper_marked(papers[i])
        for i in range(6, 10):
            assert not self.sms.is_paper_marked(papers[i])

    def test_are_all_papers_marked(self) -> None:
        """Are all questions on all (relevant) papers marked?"""
        # TODO: include this in config_test decorator
        ord = 0
        papers = Paper.objects.all()
        self.bundle = baker.make(
            Bundle,
            pdf_hash="qwerty",
        )
        # We need each paper to have at least one fixed or mobile page associated
        # so they are returned in queries of "used" papers.
        for paper in papers:
            for pg in range(1, 7):
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(FixedPage, paper=paper, image=img, version=1, page_number=pg)
            for qn in [1]:
                ord += 1
                img = baker.make(Image, bundle=self.bundle, bundle_order=ord)
                baker.make(MobilePage, paper=paper, question_index=qn, image=img)

        # all papers unmarked
        sms_instance = self.sms()
        assert not sms_instance.are_all_papers_marked()
        # papers 1-5 are "marked"
        # papers 6-8 are "unmarked"
        # papers 9, 10 are "unmarked"
        tasks = MarkingTask.objects.all()
        papers = Paper.objects.all()
        for paper in papers[0:6]:
            for j in range(1, 4):
                task = tasks.get(paper=paper, question_index=j)
                task.status = MarkingTask.COMPLETE
                task.save()
        for paper in papers[6:9]:
            for j in range(1, 3):
                task = tasks.get(paper=paper, question_index=j)
                task.status = MarkingTask.COMPLETE
                task.save()
        assert not sms_instance.are_all_papers_marked()
        # papers 1-5 are "marked"
        # papers 6-8 are "unmarked"
        # papers 9, 10 are "unmarked"
        # all papers have at least one question marked
        for paper in papers[9:11]:
            for j in range(1, 4):
                task = tasks.get(paper=paper, question_index=j)
                task.status = MarkingTask.COMPLETE
                task.save()
        assert not sms_instance.are_all_papers_marked()
        # all papers have all questions marked
        for paper in papers[1:11]:
            for j in range(1, 4):
                task = tasks.get(paper=paper, question_index=j)
                task.status = MarkingTask.COMPLETE
                task.save()
        assert sms_instance.are_all_papers_marked()

        # out of date the first paper:
        for paper in papers[1:2]:
            for j in [1]:
                task = tasks.get(paper=paper, question_index=j)
                task.status = MarkingTask.OUT_OF_DATE
                task.save()
        assert not sms_instance.are_all_papers_marked()

        # TODO: need to unit test the discard_whole_paper use case.
        # This will out of date associated marking tasks, but this
        # shouldn't return false on `are_all_papers_marked`
