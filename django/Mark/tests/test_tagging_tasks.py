# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

import pytest

from django.test import TestCase
from django.contrib.auth.models import User
from model_bakery import baker

from Mark.services import MarkingTaskService
from Mark.models import MarkingTask


class MarkingTaskServiceTaggingTests(TestCase):
    """Unit tests for tagging aspects of Mark.services.MarkingTaskService."""

    def test_tag_remove_no_such_global_tag(self):
        s = MarkingTaskService()
        task = baker.make(
            MarkingTask, question_number=1, paper__paper_number=2, code="q0002g1"
        )
        with self.assertRaisesMessage(ValueError, "No such tag"):
            s.remove_tag_text_from_task_code("no_such_tag_411d1b1443e5", task.code)

    # @pytest.mark.xfail(reason="Issue #2810")
    # def test_tag_remove_no_such_local_tag(self):
    #     s = MarkingTaskService()
    #     user = baker.make(User)
    #     s.create_tag(user, "hello")
    #     task = baker.make(
    #         MarkingTask, question_number=1, paper__paper_number=2, code="q0002g1"
    #     )
    #     with self.assertRaisesMessage(ValueError, "does not have tag"):
    #         s.remove_tag_text_from_task_code("hello", task.code)

    def test_tag_remove_invalid_code(self):
        s = MarkingTaskService()
        user = baker.make(User)
        s.create_tag(user, "hello")

        with self.assertRaisesMessage(ValueError, "not a valid task code"):
            s.remove_tag_text_from_task_code("hello", "paper_0111_invalid")

    def test_tag_remove_no_such_task(self):
        s = MarkingTaskService()
        user = baker.make(User)
        s.create_tag(user, "hello")
        with self.assertRaisesRegexp(RuntimeError, "Task .* does not exist"):
            s.remove_tag_text_from_task_code("hello", "q9999g9")
