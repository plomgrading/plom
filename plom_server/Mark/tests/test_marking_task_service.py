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
            code="0042g1",
        )
        code = "0042g1"
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
