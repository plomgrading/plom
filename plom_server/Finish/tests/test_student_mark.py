# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Aidan Murphy

from django.test import TestCase

from plom_server.Base.tests import config_test
from plom_server.Papers.models import Paper
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
