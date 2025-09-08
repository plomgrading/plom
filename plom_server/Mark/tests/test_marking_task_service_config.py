# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer

from django.test import TestCase
from django.contrib.auth.models import User
from model_bakery import baker

from plom_server.TestingSupport.config_test import config_test
from plom_server.Papers.models import Paper
from plom_server.Papers.services import PaperInfoService

from ..services import MarkingTaskService, QuestionMarkingService
from ..models import MarkingTask


class MarkingTaskTestsWithConfig(TestCase):
    @config_test()
    def test_create_task(self) -> None:
        """Test MarkingTaskService.create_task().

        Config:
        test_spec = "demo"
        num_to_produce = 2
        """
        paper1 = Paper.objects.get(paper_number=1)
        paper2 = Paper.objects.get(paper_number=2)

        mts = MarkingTaskService()
        task1 = mts.create_task(paper1, 1)
        task2 = mts.create_task(paper2, 1)

        question_version1 = PaperInfoService().get_version_from_paper_question(
            paper_number=1, question_idx=1
        )
        question_version2 = PaperInfoService().get_version_from_paper_question(
            paper_number=2, question_idx=1
        )

        self.assertEqual(task1.question_version, question_version1)
        self.assertEqual(task1.code, "0001g1")
        self.assertEqual(task2.question_version, question_version2)
        self.assertEqual(task2.code, "0002g1")

    @config_test()
    def test_marking_task_before_pqvmap(self) -> None:
        """Test that .create_task() fails if there is no QV map.

        Config:
        test_spec = "demo"
        """
        paper1 = baker.make(Paper, paper_number=1)

        with self.assertRaises(RuntimeError):
            mts = MarkingTaskService()
            mts.create_task(paper1, 1)

    @config_test()
    def test_get_first_filter(self) -> None:
        """Test get_first_available_task() with a specified question and version.

        Config:
        test_spec = "tiny_spec.toml"
        qvmap = "tiny_qvmap.toml"
        auto_init_tasks = true
        """
        task1 = MarkingTask.objects.get(question_index=1, question_version=1)
        task2 = MarkingTask.objects.get(question_index=1, question_version=2)
        task3 = MarkingTask.objects.get(question_index=2, question_version=1)
        task4 = MarkingTask.objects.get(question_index=2, question_version=2)

        self.assertEqual(QuestionMarkingService.get_first_available_task(), task1)
        self.assertEqual(
            QuestionMarkingService.get_first_available_task(question_idx=1, version=2),
            task2,
        )
        self.assertEqual(
            QuestionMarkingService.get_first_available_task(question_idx=2, version=1),
            task3,
        )
        self.assertEqual(
            QuestionMarkingService.get_first_available_task(question_idx=2, version=2),
            task4,
        )

    @config_test()
    def test_user_can_update_task(self) -> None:
        """Test MarkingTaskService.user_can_update_task().

        Config:
        test_spec = "tiny_spec.toml"
        num_to_produce = 3
        auto_init_tasks = true
        """
        user1: User = baker.make(User)
        user2: User = baker.make(User)

        task1 = MarkingTask.objects.get(code="0001g1")
        task1.assigned_user = user1
        task1.status = MarkingTask.OUT
        task1.save()

        task2 = MarkingTask.objects.get(code="0002g1")

        task3 = MarkingTask.objects.get(code="0003g1")
        task3.assigned_user = user1
        task3.status = MarkingTask.COMPLETE
        task3.save()

        task4 = MarkingTask.objects.get(code="0001g2")
        task4.assigned_user = user2
        task4.status = MarkingTask.COMPLETE
        task4.save()

        task5 = MarkingTask.objects.get(code="0002g2")
        task5.assigned_user = user2
        task5.status = MarkingTask.OUT
        task5.save()

        task6 = MarkingTask.objects.get(code="0003g2")
        task6.assigned_user = user1
        task6.status = MarkingTask.OUT_OF_DATE
        task6.save()

        srv = QuestionMarkingService
        self.assertTrue(srv._user_can_update_task(user1, task1))
        self.assertFalse(srv._user_can_update_task(user1, task2))
        self.assertTrue(srv._user_can_update_task(user1, task3))
        self.assertFalse(srv._user_can_update_task(user1, task4))
        self.assertFalse(srv._user_can_update_task(user1, task5))
        self.assertFalse(srv._user_can_update_task(user1, task6))

    @config_test()
    def test_task_priorities_by_papernum(self) -> None:
        """Test setting task priority by paper number.

        Config:
        test_spec = "tiny_spec.toml"
        num_to_produce = 2
        auto_init_tasks = true
        """
        task1 = MarkingTask.objects.get(code="0001g1")
        task2 = MarkingTask.objects.get(code="0001g2")
        task3 = MarkingTask.objects.get(code="0002g1")

        self.assertEqual(QuestionMarkingService.get_first_available_task(), task1)

        task1.status = MarkingTask.COMPLETE
        task1.save()

        self.assertEqual(QuestionMarkingService.get_first_available_task(), task2)

        # keep linter happy
        del task3
