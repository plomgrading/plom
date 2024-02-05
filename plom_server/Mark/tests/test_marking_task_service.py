# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer

from django.test import TestCase
from django.contrib.auth.models import User
from model_bakery import baker

from ..services import MarkingTaskService, mark_task
from ..models import MarkingTask


class MarkingTaskServiceTests(TestCase):
    """Unit tests for Mark.services.MarkingTaskService.

    Also tests some of the function-based services in mark_task.
    """

    def test_unpack_code(self):
        """Test mark_task.unpack_code()."""

        with self.assertRaises(AssertionError):
            mark_task.unpack_code("")

        with self.assertRaises(AssertionError):
            mark_task.unpack_code("astringthatdoesn'tstartwithq")

        with self.assertRaises(AssertionError):
            mark_task.unpack_code("qastrinGthatdoesn'tcontainalowercaseG")

        with self.assertRaises(ValueError):
            mark_task.unpack_code("q000qge")

        paper_number, question_number = mark_task.unpack_code("q0001g2")
        self.assertEqual(paper_number, 1)
        self.assertEqual(question_number, 2)

    def test_unpack_code_additional_tests(self):
        with self.assertRaises(AssertionError):
            mark_task.unpack_code("g0001q2")

        _, q1 = mark_task.unpack_code("q0001g2")
        _, q2 = mark_task.unpack_code("q0001g02")

        self.assertEqual(q1, q2)

        _, q1 = mark_task.unpack_code("q0001g2")
        _, q2 = mark_task.unpack_code("q0001g22")

        self.assertNotEqual(q1, q2)

        p1, q1 = mark_task.unpack_code(
            "q1234567890987654321g8888888855555555123412341324"
        )
        p2, q2 = mark_task.unpack_code(
            "q1234567890987654321g9090909090909090909090909090"
        )
        p3, q3 = mark_task.unpack_code(
            "q9876543100123456789g9090909090909090909090909090"
        )

        self.assertEqual(p1, p2)
        self.assertNotEqual(p1, p3)
        self.assertEqual(q2, q3)
        self.assertNotEqual(q1, q3)

        p1, q1 = mark_task.unpack_code("q8g9")
        self.assertEqual(p1, 8)
        self.assertEqual(q1, 9)

    def test_get_latest_task_no_paper_nor_question(self):
        s = MarkingTaskService()
        with self.assertRaisesRegex(RuntimeError, "Task .*does not exist"):
            s.get_task_from_code("q0042g42")

    def test_get_latest_task_has_paper_but_no_question(self):
        s = MarkingTaskService()
        task = baker.make(
            MarkingTask, question_number=1, paper__paper_number=42, code="q0042g1"
        )
        code = "q0042g9"
        assert task.code != code
        with self.assertRaisesRegex(RuntimeError, "Task .*does not exist"):
            s.get_task_from_code(code)

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

    def test_surrender_all_tasks(self):
        user = baker.make(User)
        task1 = baker.make(MarkingTask, assigned_user=user, status=MarkingTask.OUT)
        task2 = baker.make(MarkingTask, assigned_user=user, status=MarkingTask.OUT)
        mts = MarkingTaskService()

        mts.surrender_all_tasks(user)
        task1.refresh_from_db()
        task2.refresh_from_db()
        self.assertEqual(task1.status, MarkingTask.TO_DO)
        self.assertEqual(task2.status, MarkingTask.TO_DO)
