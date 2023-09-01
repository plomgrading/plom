# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer

from django.test import TestCase
from django.contrib.auth.models import User
from model_bakery import baker

from Base.tests import config_test
from Preparation.models import StagingPQVMapping
from Papers.models import Paper

from ..services import MarkingTaskService
from ..models import MarkingTask, MarkingTaskPriority


class MarkingTaskTestsWithConfig(TestCase):
    @config_test()
    def test_create_task(self):
        """Test MarkingTaskService.create_task()

        Config:
        test_spec = "demo"
        num_to_produce = 2
        """

        paper1 = Paper.objects.get(paper_number=1)
        paper2 = Paper.objects.get(paper_number=2)

        mts = MarkingTaskService()
        task1 = mts.create_task(paper1, 1)
        task2 = mts.create_task(paper2, 1)

        question_version1 = StagingPQVMapping.objects.get(
            paper_number=1, question=1
        ).version
        question_version2 = StagingPQVMapping.objects.get(
            paper_number=2, question=1
        ).version

        self.assertEqual(task1.question_version, question_version1)
        self.assertAlmostEqual(task1.code, "q0001g1")
        self.assertEqual(task2.question_version, question_version2)
        self.assertEqual(task2.code, "q0002g1")

    @config_test()
    def test_marking_task_before_pqvmap(self):
        """Test that .create_task() fails if there is no QV map.

        Config:
        test_spec = "demo"
        """
        paper1 = baker.make(Paper, paper_number=1)

        with self.assertRaises(RuntimeError):
            mts = MarkingTaskService()
            mts.create_task(paper1, 1)

    @config_test()
    def test_get_first_filter(self):
        """Test MarkingTaskService.get_first_available_task() with a specified question and version.

        Config:
        test_spec = "config_files/tiny_spec.toml"
        qvmap = "config_files/tiny_qvmap.toml"
        auto_init_tasks = true
        """
        task1 = MarkingTask.objects.get(question_number=1, question_version=1)
        task2 = MarkingTask.objects.get(question_number=1, question_version=2)
        task3 = MarkingTask.objects.get(question_number=2, question_version=1)
        task4 = MarkingTask.objects.get(question_number=2, question_version=2)

        mts = MarkingTaskService()

        self.assertEqual(mts.get_first_available_task(), task1)
        self.assertEqual(mts.get_first_available_task(1, 2), task2)
        self.assertEqual(mts.get_first_available_task(2, 1), task3)
        self.assertEqual(mts.get_first_available_task(2, 2), task4)

    @config_test()
    def test_user_can_update_task(self):
        """Test MarkingTaskService.user_can_update_task()

        Config:
        test_spec = "config_files/tiny_spec.toml"
        num_to_produce = 3
        auto_init_tasks = true
        """
        user1 = baker.make(User)
        user2 = baker.make(User)

        task1 = MarkingTask.objects.get(code="q0001g1")
        task1.assigned_user = user1
        task1.status = MarkingTask.OUT
        task1.save()

        task2 = MarkingTask.objects.get(code="q0002g1")

        task3 = MarkingTask.objects.get(code="q0003g1")
        task3.assigned_user = user1
        task3.status = MarkingTask.COMPLETE
        task3.save()

        task4 = MarkingTask.objects.get(code="q0001g2")
        task4.assigned_user = user2
        task4.status = MarkingTask.COMPLETE
        task4.save()

        task5 = MarkingTask.objects.get(code="q0002g2")
        task5.assigned_user = user2
        task5.status = MarkingTask.OUT
        task5.save()

        task6 = MarkingTask.objects.get(code="q0003g2")
        task6.assigned_user = user1
        task6.status = MarkingTask.OUT_OF_DATE
        task6.save()

        mts = MarkingTaskService()
        self.assertTrue(mts.user_can_update_task(user1, task1.code))
        self.assertFalse(mts.user_can_update_task(user1, task2.code))
        self.assertTrue(mts.user_can_update_task(user1, task3.code))
        self.assertFalse(mts.user_can_update_task(user1, task4.code))
        self.assertFalse(mts.user_can_update_task(user1, task5.code))
        self.assertFalse(mts.user_can_update_task(user1, task6.code))

    @config_test()
    def test_task_priorities_by_papernum(self):
        """Test setting task priority by paper number.

        Config:
        test_spec = "config_files/tiny_spec.toml"
        num_to_produce = 2
        auto_init_tasks = true
        """
        mts = MarkingTaskService()
        task1 = MarkingTask.objects.get(code="q0001g1")
        task2 = MarkingTask.objects.get(code="q0001g2")
        task3 = MarkingTask.objects.get(code="q0002g1")

        self.assertEqual(mts.get_first_available_task(), task1)

        task1.status = MarkingTask.COMPLETE
        task1.save()

        self.assertEqual(mts.get_first_available_task(), task2)
