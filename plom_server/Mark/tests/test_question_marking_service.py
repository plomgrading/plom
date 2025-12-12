# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer

from django.test import TestCase
from model_bakery import baker

from ..services import QuestionMarkingService
from ..models import MarkingTask


class QuestionMarkingServiceTests(TestCase):
    def test_get_first_available_task(self) -> None:
        baker.make(
            MarkingTask,
            status=MarkingTask.COMPLETE,
            paper__paper_number=1,
            code="1",
        )
        baker.make(MarkingTask, status=MarkingTask.OUT, paper__paper_number=2, code="2")
        task3 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            paper__paper_number=3,
            code="3",
            marking_priority=2.0,
        )
        baker.make(
            MarkingTask, status=MarkingTask.COMPLETE, paper__paper_number=4, code="4"
        )
        task5 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            paper__paper_number=5,
            code="5",
            marking_priority=1.0,
        )

        task = QuestionMarkingService.get_first_available_task()
        self.assertEqual(task, task3)
        task3.status = MarkingTask.OUT
        task3.save()

        next_task = QuestionMarkingService.get_first_available_task()
        self.assertEqual(next_task, task5)
