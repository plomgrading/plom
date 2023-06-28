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

    def test_unpack_code(self):
        """
        Test MarkingTaskService.unpack_code
        """

        mts = MarkingTaskService()
        with self.assertRaises(AssertionError):
            mts.unpack_code("")

        with self.assertRaises(AssertionError):
            mts.unpack_code("astringthatdoesn'tstartwithq")

        with self.assertRaises(AssertionError):
            mts.unpack_code("qastrinGthatdoesn'tcontainalowercaseG")

        with self.assertRaises(ValueError):
            mts.unpack_code("q000qge")

        paper_number, question_number = mts.unpack_code("q0001g2")
        self.assertEqual(paper_number, 1)
        self.assertEqual(question_number, 2)

    def test_unpack_code_additional_tests(self):
        mts = MarkingTaskService()
        with self.assertRaises(AssertionError):
            mts.unpack_code("g0001q2")

        _, q1 = mts.unpack_code("q0001g2")
        _, q2 = mts.unpack_code("q0001g02")

        self.assertEqual(q1, q2)

        _, q1 = mts.unpack_code("q0001g2")
        _, q2 = mts.unpack_code("q0001g22")

        self.assertNotEqual(q1, q2)

        p1, q1 = mts.unpack_code("q1234567890987654321g8888888855555555123412341324")
        p2, q2 = mts.unpack_code("q1234567890987654321g9090909090909090909090909090")
        p3, q3 = mts.unpack_code("q9876543100123456789g9090909090909090909090909090")

        self.assertEqual(p1, p2)
        self.assertNotEqual(p1, p3)
        self.assertEqual(q2, q3)
        self.assertNotEqual(q1, q3)

        p1, q1 = mts.unpack_code("q8g9")
        self.assertEqual(p1, 8)
        self.assertEqual(q1, 9)

    def test_get_first_available_task(self):
        """
        Test MarkingTaskService.get_first_available_task()
        """

        task1 = baker.make(
            MarkingTask, status=MarkingTask.COMPLETE, paper__paper_number=1, code="1"
        )
        task2 = baker.make(
            MarkingTask, status=MarkingTask.OUT, paper__paper_number=2, code="2"
        )
        task3 = baker.make(
            MarkingTask, status=MarkingTask.TO_DO, paper__paper_number=3, code="3"
        )
        task4 = baker.make(
            MarkingTask, status=MarkingTask.COMPLETE, paper__paper_number=4, code="4"
        )
        task5 = baker.make(
            MarkingTask, status=MarkingTask.TO_DO, paper__paper_number=5, code="5"
        )

        mts = MarkingTaskService()
        task = mts.get_first_available_task()
        self.assertEqual(task, task3)
        task3.status = MarkingTask.OUT
        task3.save()

        next_task = mts.get_first_available_task()
        self.assertEqual(next_task, task5)

    def test_get_first_filter(self):
        """
        Test MarkingTaskService.get_first_available_task() with a specified question and version
        """

        task1 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=1,
            question_version=1,
            paper__paper_number=1,
            code="1",
        )
        task2 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=1,
            question_version=2,
            paper__paper_number=2,
            code="2",
        )
        task3 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
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
        task = baker.make(MarkingTask, status=MarkingTask.TO_DO)

        mts = MarkingTaskService()
        mts.assign_task_to_user(user1, task)
        task.refresh_from_db()
        self.assertEqual(task.status, MarkingTask.OUT)
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
        task = baker.make(MarkingTask, status=MarkingTask.OUT)
        mts = MarkingTaskService()

        mts.surrender_task(user, task)
        task.refresh_from_db()
        self.assertEqual(task.status, MarkingTask.TO_DO)

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
            status=MarkingTask.OUT,
            assigned_user=user,
            paper=paper1,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=None,
            paper=paper2,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0003g1",
            status=MarkingTask.OUT,
            assigned_user=other_user,
            paper=paper3,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0004g1",
            status=MarkingTask.COMPLETE,
            assigned_user=user,
            paper=paper4,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0005g1",
            status=MarkingTask.COMPLETE,
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


class TestMarkingTasksWithFixtures(TestCase):
    fixtures = ["test_spec.json", "preparation.json", "papers.json"]

    def test_create_task(self):
        """Test MarkingTaskService.create_task()"""
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

    def test_marking_task_before_pqvmap(self):
        """Test that .create_task() fails if there is no QV map."""
        paper1 = Paper.objects.get(paper_number=1)

        # Remove QV map for testing purposes
        StagingPQVMapping.objects.all().delete()

        with self.assertRaises(RuntimeError):
            mts = MarkingTaskService()
            mts.create_task(paper1, 1)
