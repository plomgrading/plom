# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from django.contrib.auth.models import User
from django.test import TestCase
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from ..models import MarkingTask, MarkingTaskTag
from ..services import MarkingTaskService


class MarkingTaskServiceTaggingTests(TestCase):
    """Unit tests for tagging aspects of Mark.services.MarkingTaskService."""

    def test_tag_create_tag(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        tag = s.get_or_create_tag(user, "tag")
        assert tag.text == "tag"
        tag2 = s.get_or_create_tag(user, "tag2")
        assert tag2.text != tag.text
        # probably exactly 2 but I don't quite understand when things are reset
        assert len(s.get_all_tags()) >= 2

    def test_tag_create_invalid_tag(self) -> None:
        # note validity is mostly tested elsewhere
        s = MarkingTaskService()
        user: User = baker.make(User)
        with self.assertRaisesMessage(ValidationError, "disallowed char"):
            s.get_or_create_tag(user, "  spaces ")
        with self.assertRaisesMessage(ValidationError, "disallowed char"):
            s.get_or_create_tag(user, "symbols_$&<b>")

    def test_tag_create_duplicate_tag_issue3580(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        tag1 = s.get_or_create_tag(user, "hello")
        tag2 = s.get_or_create_tag(user, "hello")
        assert tag1.pk == tag2.pk

    def test_get_all_tags(self) -> None:
        s = MarkingTaskService()
        assert s.get_all_tags() == []
        baker.make(MarkingTaskTag)
        assert len(s.get_all_tags()) == 1

    def test_get_all_tags_tuples_with_ints(self) -> None:
        s = MarkingTaskService()
        assert s.get_all_tags() == []
        user: User = baker.make(User)
        s.get_or_create_tag(user, "mytag1")
        s.get_or_create_tag(user, "mytag2")
        a, b = s.get_all_tags()
        n, t = a
        assert isinstance(n, int)
        assert t == "mytag1"
        n, t = b
        assert isinstance(n, int)
        assert t == "mytag2"

    def test_tag_task_invalid_tag(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        task = baker.make(
            MarkingTask, question_index=1, paper__paper_number=2, code="q0002g1"
        )
        with self.assertRaisesMessage(ValidationError, "disallowed char"):
            tag_text = "  spaces and symbols $&<b> "
            s.add_tag_text_from_task_code(tag_text, task.code, user)

    def test_tag_task(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        # tag = s._create_tag(user, "hello")
        tag = baker.make(MarkingTaskTag)
        task = baker.make(
            MarkingTask, question_index=1, paper__paper_number=2, code="q0002g1"
        )
        s.add_tag_text_from_task_code(tag.text, task.code, user)

    def test_tag_task_twice_same(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        tag = baker.make(MarkingTaskTag)
        task = baker.make(
            MarkingTask, question_index=1, paper__paper_number=2, code="q0002g1"
        )
        s.add_tag_text_from_task_code(tag.text, task.code, user)
        s.add_tag_text_from_task_code(tag.text, task.code, user)

    def test_tag_task_twice(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        tag1 = baker.make(MarkingTaskTag)
        tag2 = baker.make(MarkingTaskTag)
        task = baker.make(
            MarkingTask, question_index=1, paper__paper_number=2, code="q0002g1"
        )
        s.add_tag_text_from_task_code(tag1.text, task.code, user)
        s.add_tag_text_from_task_code(tag2.text, task.code, user)

    def test_tag_task_autocreate_none_existing_tag(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        task = baker.make(
            MarkingTask, question_index=1, paper__paper_number=2, code="q0002g1"
        )
        s.add_tag_text_from_task_code("a_new_tag", task.code, user)

    def test_tag_task_invalid_task_code(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        with self.assertRaisesMessage(ValueError, "not a valid task code"):
            s.add_tag_text_from_task_code("hello", "paper_0111_invalid", user)

    def test_tag_task_no_such_task_code(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        with self.assertRaisesRegex(RuntimeError, "Task .* does not exist"):
            s.add_tag_text_from_task_code("hello", "q9999g9", user)

    def test_get_tags_for_task(self) -> None:
        s = MarkingTaskService()
        task = baker.make(
            MarkingTask, question_index=1, paper__paper_number=2, code="q0002g1"
        )
        tags = s.get_tags_for_task(task.code)
        assert tags == []
        user: User = baker.make(User)
        s.add_tag_text_from_task_code("a_new_tag", task.code, user)
        tags = s.get_tags_for_task(task.code)
        assert "a_new_tag" in tags
        s.add_tag_text_from_task_code("one_more", task.code, user)
        tags = s.get_tags_for_task(task.code)
        assert "one_more" in tags
        assert "a_new_tag" in tags

    def test_get_tags_for_task_invalid_task(self) -> None:
        s = MarkingTaskService()
        with self.assertRaisesMessage(ValueError, "not a valid task code"):
            s.get_tags_for_task("paper_0111_invalid")

    def test_get_tags_for_task_no_such_task(self) -> None:
        s = MarkingTaskService()
        with self.assertRaisesRegex(RuntimeError, "Task .* does not exist"):
            s.get_tags_for_task("q9999g9")


class MarkingTaskServiceRemovingTaggingTests(TestCase):
    """Unit tests for removing tags in Mark.services.MarkingTaskService."""

    def test_tag_remove_no_such_global_tag(self) -> None:
        s = MarkingTaskService()
        task = baker.make(
            MarkingTask, question_index=1, paper__paper_number=2, code="q0002g1"
        )
        with self.assertRaisesMessage(ValueError, "No such tag"):
            s.remove_tag_text_from_task_code("no_such_tag_411d1b1443e5", task.code)

    def test_tag_remove_no_such_local_tag(self) -> None:
        # this tests issue #2810 - which was fixed in !2792
        # now an appropriate exception is raised.
        s = MarkingTaskService()
        user: User = baker.make(User)
        s.get_or_create_tag(user, "hello")
        task = baker.make(
            MarkingTask, question_index=1, paper__paper_number=2, code="q0002g1"
        )
        with self.assertRaisesMessage(ValueError, "does not have tag"):
            s.remove_tag_text_from_task_code("hello", task.code)

    def test_tag_remove_invalid_code(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        s.get_or_create_tag(user, "hello")

        with self.assertRaisesMessage(ValueError, "not a valid task code"):
            s.remove_tag_text_from_task_code("hello", "paper_0111_invalid")

    def test_tag_remove_no_such_task(self) -> None:
        s = MarkingTaskService()
        user: User = baker.make(User)
        s.get_or_create_tag(user, "hello")
        with self.assertRaisesRegex(RuntimeError, "Task .*does not exist"):
            s.remove_tag_text_from_task_code("hello", "q9999g9")
