# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Aidan Murphy
# Copyright (C) 2025 Colin B. Macdonald

from django.contrib.auth.models import User
from django.test import TestCase
from model_bakery import baker

from plom_server.Base.tests import config_test
from plom_server.Papers.models import Paper, Image, MobilePage, Bundle, QuestionPage
from plom_server.Mark.models import MarkingTask
from plom_server.Scan.services import ManageDiscardService
from ..services import StudentMarkService


class TestStudentMarkService(TestCase):
    """Tests for Finish.service.StudentMarkService."""

    sms = StudentMarkService

    @config_test(
        {
            "test_spec": "demo",
            "test_sources": "demo",
            "classlist": "demo",
            "num_to_produce": 10,
            "auto_init_tasks": True,
        }
    )
    def setUp(self) -> None:
        self.user0: User = baker.make(User, username="user0")

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
                baker.make(
                    QuestionPage,
                    paper=paper,
                    image=img,
                    version=1,
                    page_number=pg,
                    question_index=(pg % 5),
                )
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

        # discard a paper - this will out of date marking tasks
        # but they belong to a paper which is now 'unused'
        ManageDiscardService().discard_whole_paper_by_number(
            self.user0, papers[9].paper_number, dry_run=False
        )
        assert MarkingTask.objects.filter(status=MarkingTask.OUT_OF_DATE).exists()
        assert sms_instance.are_all_papers_marked()

        # out of date the first paper:
        for paper in papers[1:2]:
            for j in [1]:
                task = tasks.get(paper=paper, question_index=j)
                task.status = MarkingTask.OUT_OF_DATE
                task.save()
        assert not sms_instance.are_all_papers_marked()
