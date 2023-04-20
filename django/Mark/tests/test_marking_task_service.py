# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates

from django.test import TestCase
from django.contrib.auth.models import User
from model_bakery import baker

from Preparation.models import StagingPQVMapping
from Papers.models import Paper

from Mark.services import MarkingTaskService
from Mark.models import MarkingTask


class MarkingTaskServiceTests(TestCase):
    """
    Unit tests for Mark.services.MarkingTaskService
    """

    def test_create_task(self):
        """
        Test MarkingTaskService.create_task()
        """

        paper1 = baker.make(Paper, paper_number=1)
        paper2 = baker.make(Paper, paper_number=2)

        mts = MarkingTaskService()
        with self.assertRaisesMessage(
            RuntimeError, "Server does not have a question-version map."
        ):
            mts.create_task(1, 1)

        baker.make(StagingPQVMapping, paper_number=1, question=1, version=1)
        baker.make(StagingPQVMapping, paper_number=1, question=2, version=1)
        baker.make(StagingPQVMapping, paper_number=2, question=1, version=2)
        baker.make(StagingPQVMapping, paper_number=2, question=2, version=2)

        task1 = mts.create_task(paper1, 1)
        self.assertEqual(task1.question_version, 1)
        self.assertEqual(task1.code, "q0001g1")

        task2 = mts.create_task(paper2, 1)
        self.assertEqual(task2.question_version, 2)
        self.assertEqual(task2.code, "q0002g1")

    def test_unpack_code(self):
        """
        Test MarkingTaskService.unpack_code
        """

        mts = MarkingTaskService()
        with self.assertRaises(AssertionError):
            mts.unpack_code("")

        with self.assertRaises(AssertionError):
            mts.unpack_code("astringthatistoolong")

        with self.assertRaises(ValueError):
            mts.unpack_code("q000qge")

        paper_number, question_number = mts.unpack_code("q0001g2")
        self.assertEqual(paper_number, 1)
        self.assertEqual(question_number, 2)

    def test_get_first_available_task(self):
        """
        Test MarkingTaskService.get_first_available_task()
        """

        task1 = baker.make(
            MarkingTask, status="complete", paper__paper_number=1, code="1"
        )
        task2 = baker.make(MarkingTask, status="out", paper__paper_number=2, code="2")
        task3 = baker.make(MarkingTask, status="todo", paper__paper_number=3, code="3")
        task4 = baker.make(
            MarkingTask, status="complete", paper__paper_number=4, code="4"
        )
        task5 = baker.make(MarkingTask, status="todo", paper__paper_number=5, code="5")

        mts = MarkingTaskService()
        task = mts.get_first_available_task()
        self.assertEqual(task, task3)
        task3.status = "out"
        task3.save()

        next_task = mts.get_first_available_task()
        self.assertEqual(next_task, task5)

    def test_get_first_filter(self):
        """
        Test MarkingTaskService.get_first_available_task() with a specified question and version
        """

        task1 = baker.make(
            MarkingTask,
            status="todo",
            question_number=1,
            question_version=1,
            paper__paper_number=1,
            code="1",
        )
        task2 = baker.make(
            MarkingTask,
            status="todo",
            question_number=1,
            question_version=2,
            paper__paper_number=2,
            code="2",
        )
        task3 = baker.make(
            MarkingTask,
            status="todo",
            question_number=2,
            question_version=2,
            paper__paper_number=3,
            code="3",
        )

        mts = MarkingTaskService()
        task = mts.get_first_available_task(1, 2)
        self.assertEqual(task, task2)

    def test_assign_task_to_user(self):
        """
        Test MarkingTaskService.assign_task_to_user()
        """

        user1 = baker.make(User)
        user2 = baker.make(User)
        task = baker.make(MarkingTask, status="todo")

        mts = MarkingTaskService()
        mts.assign_task_to_user(user1, task)
        task.refresh_from_db()
        self.assertEqual(task.status, "out")
        self.assertEqual(task.assigned_user, user1)

        with self.assertRaisesMessage(RuntimeError, "Task is currently assigned."):
            mts.assign_task_to_user(user2, task)

        task.refresh_from_db()
        self.assertEqual(task.assigned_user, user1)

    def test_surrender_task(self):
        """
        Test MarkingTaskService.surrender_task()
        """

        user = baker.make(User)
        task = baker.make(MarkingTask, status="out")
        mts = MarkingTaskService()

        mts.surrender_task(user, task)
        task.refresh_from_db()
        self.assertEqual(task.status, "todo")

    def test_user_can_update_task(self):
        """
        Test MarkingTaskService.user_can_update_task()
        """

        user = baker.make(User)
        other_user = baker.make(User)
        paper1 = baker.make(Paper, paper_number=1)
        paper2 = baker.make(Paper, paper_number=2)
        paper3 = baker.make(Paper, paper_number=3)
        paper4 = baker.make(Paper, paper_number=4)
        paper5 = baker.make(Paper, paper_number=5)

        baker.make(
            MarkingTask,
            code="q0001g1",
            status="out",
            assigned_user=user,
            paper=paper1,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0002g1",
            status="todo",
            assigned_user=None,
            paper=paper2,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0003g1",
            status="out",
            assigned_user=other_user,
            paper=paper3,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0004g1",
            status="complete",
            assigned_user=user,
            paper=paper4,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0005g1",
            status="complete",
            assigned_user=other_user,
            paper=paper5,
            question_number=1,
        )

        mts = MarkingTaskService()
        self.assertTrue(mts.user_can_update_task(user, "q0001g1"))
        self.assertFalse(mts.user_can_update_task(user, "q0002g1"))
        self.assertFalse(mts.user_can_update_task(user, "q0003g1"))
        self.assertTrue(mts.user_can_update_task(user, "q0004g1"))
        self.assertFalse(mts.user_can_update_task(user, "q0005g1"))
