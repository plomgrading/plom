# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
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

    def test_unpack_code(self) -> None:
        """Test mark_task.unpack_code()."""
        with self.assertRaises(ValueError):
            mark_task.unpack_code("")

        with self.assertRaises(ValueError):
            mark_task.unpack_code("astringthatdoesn'tstartwithq")

        with self.assertRaises(ValueError):
            mark_task.unpack_code("qastrinGthatdoesn'tcontainalowercaseG")

        with self.assertRaises(ValueError):
            mark_task.unpack_code("000qge")

        paper_number, question_index = mark_task.unpack_code("0001g2")
        self.assertEqual(paper_number, 1)
        self.assertEqual(question_index, 2)

    def test_unpack_code_optional_legacy_leading_q(self) -> None:
        p, q = mark_task.unpack_code("q0001g2")
        self.assertEqual(p, 1)
        self.assertEqual(q, 2)
        p, q = mark_task.unpack_code("q8g9")
        self.assertEqual(p, 8)
        self.assertEqual(q, 9)

    def test_unpack_code_additional_tests(self) -> None:
        with self.assertRaises(ValueError):
            mark_task.unpack_code("g0001q2")

        __, q1 = mark_task.unpack_code("0001g2")
        __, q2 = mark_task.unpack_code("0001g02")

        self.assertEqual(q1, q2)

        __, q1 = mark_task.unpack_code("0001g2")
        __, q2 = mark_task.unpack_code("0001g22")

        self.assertNotEqual(q1, q2)

        p1, q1 = mark_task.unpack_code("1234567g88888")
        p2, q2 = mark_task.unpack_code("1234567g90909")
        p3, q3 = mark_task.unpack_code("9876543g90909")

        self.assertEqual(p1, p2)
        self.assertNotEqual(p1, p3)
        self.assertEqual(q2, q3)
        self.assertNotEqual(q1, q3)

        p1, q1 = mark_task.unpack_code("8g9")
        self.assertEqual(p1, 8)
        self.assertEqual(q1, 9)

    def test_get_latest_task_no_paper_nor_question(self) -> None:
        s = MarkingTaskService()
        with self.assertRaisesRegex(RuntimeError, "Task .*does not exist"):
            s.get_task_from_code("0042g42")

    def test_get_latest_task_has_paper_but_no_question(self) -> None:
        s = MarkingTaskService()
        task = baker.make(
            MarkingTask, question_index=1, paper__paper_number=42, code="0042g1"
        )
        code = "0042g9"
        assert task.code != code
        with self.assertRaisesRegex(RuntimeError, "Task .*does not exist"):
            s.get_task_from_code(code)

    def test_get_latest_task_asking_for_wrong_version(self) -> None:
        task = baker.make(
            MarkingTask,
            question_index=1,
            question_version=2,
            paper__paper_number=42,
            code="q0042g1",
        )
        code = "q0042g1"
        assert task.code == code
        mark_task.get_latest_task(42, 1, question_version=2)
        with self.assertRaisesRegex(ValueError, "wrong version"):
            mark_task.get_latest_task(42, 1, question_version=1)

    def test_assign_task_to_user(self) -> None:
        """Test MarkingTaskService.assign_task_to_user()."""
        user1: User = baker.make(User)
        user2: User = baker.make(User)
        task = baker.make(MarkingTask, status=MarkingTask.TO_DO)

        MarkingTaskService.assign_task_to_user(task.pk, user1)
        task.refresh_from_db()
        self.assertEqual(task.status, MarkingTask.OUT)
        self.assertEqual(task.assigned_user, user1)

        with self.assertRaisesRegex(RuntimeError, "Task .* not available.* assigned"):
            MarkingTaskService.assign_task_to_user(task.pk, user2)

        task.refresh_from_db()
        self.assertEqual(task.assigned_user, user1)

    def test_surrender_all_tasks(self) -> None:
        user: User = baker.make(User)
        task1 = baker.make(MarkingTask, assigned_user=user, status=MarkingTask.OUT)
        task2 = baker.make(MarkingTask, assigned_user=user, status=MarkingTask.OUT)

        MarkingTaskService.surrender_all_tasks(user)
        task1.refresh_from_db()
        task2.refresh_from_db()
        self.assertEqual(task1.status, MarkingTask.TO_DO)
        self.assertEqual(task2.status, MarkingTask.TO_DO)

    # TODO: test MarkingTaskService._validate_and_clean_marking_data(...)
