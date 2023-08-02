# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase

from model_bakery import baker
from rest_framework.exceptions import ValidationError

from Mark.models.annotations import Annotation
from Mark.models.tasks import MarkingTask
from Papers.models.paper_structure import Paper
from ..models import Rubric
from ..services import RubricService


# helper function: extract a rubric dict from Rubric model
def _rubric_to_dict(x):
    # convert to dict and discard hidden underscore fields
    d = {k: v for k, v in x.__dict__.items() if not k.startswith("_")}
    d.pop("user_id")
    # overwrite id with key: client uses "id" not "key"
    d.pop("id")
    d["id"] = d.pop("key")
    return d


class RubricServiceTests_exceptions(TestCase):
    def test_no_user(self):
        rub = {
            "kind": "neutral",
            "value": 0,
            "text": "qwerty",
            "username": "XXX_no_such_user_XXX",
            "question": 1,
        }

        rub2 = {
            "kind": "neutral",
            "value": 0,
            "text": "qwerty",
            "question": 1,
        }
        with self.assertRaises(ObjectDoesNotExist):
            RubricService().create_rubric(rub)

        with self.assertRaises(KeyError):
            RubricService().create_rubric(rub2)
    
    def test_no_kind(self):
        baker.make(User, username="Liam")

        rub = {
            "kind": "No kind",
            "value": 0,
            "text": "qwerty",
            "username": "Liam",
            "question": 1,
        }

        rub2 = {
            "value": 0,
            "text": "qwerty",
            "username": "Liam",
            "question": 1,
        }

        with self.assertRaises(ValidationError):
            RubricService().create_rubric(rub)

        with self.assertRaises(KeyError):
            RubricService().create_rubric(rub2)


class RubricServiceTests(TestCase):
    """Tests for `Rubric.service.RubricService()`."""

    def setUp(self):
        user1 = baker.make(User, username="Liam")
        user2 = baker.make(User, username="Olivia")

        self.neutral_rubric = baker.make(
            Rubric,
            kind="neutral",
            display_delta=".",
            value=0,
            out_of=0,
            text="qwert",
            question=1,
            user=user1,
            tags="",
            meta="asdfg",
            versions=[],
            parameters=[],
        )

        self.modified_neutral_rubric = baker.make(
            Rubric,
            kind="neutral",
            display_delta=".",
            value=0,
            out_of=0,
            text="yuiop",
            question=1,
            user=user2,
            tags="",
            meta="hjklz",
            versions=[],
            parameters=[],
        )

        self.relative_rubric = baker.make(
            Rubric,
            kind="relative",
            display_delta="+3",
            value=3,
            out_of=0,
            text="yuiop",
            question=1,
            user=user2,
            tags="",
            meta="hjklz",
            versions=[],
            parameters=[],
        )

        self.modified_relative_rubric = baker.make(
            Rubric,
            kind="relative",
            display_delta="+3",
            value=3,
            user=user2,
        )

        self.absolute_rubric = baker.make(
            Rubric,
            kind="absolute",
            display_delta="2 of 5",
            value=2,
            out_of=5,
            text="mnbvc",
            question=3,
            user=user1,
            tags="",
            meta="lkjhg",
            versions=[],
            parameters=[],
        )

        self.modified_absolute_rubric = baker.make(
            Rubric,
            kind="absolute",
            display_delta="3 of 5",
            value=3,
            out_of=5,
            user=user2,
        )

        return super().setUp()

    def test_create_neutral_rubric(self):
        """Test RubricService.create_rubric() to create a neural rubric."""
        simulated_client_data = {
            "kind": "neutral",
            "display_delta": ".",
            "value": 0,
            "out_of": 0,
            "text": "qwert",
            "tags": "",
            "meta": "asdfg",
            "username": "Liam",
            "question": 1,
            "versions": [],
            "parameters": [],
        }
        r = RubricService().create_rubric(simulated_client_data)

        self.assertEqual(r.kind, self.neutral_rubric.kind)
        self.assertEqual(r.display_delta, self.neutral_rubric.display_delta)
        self.assertEqual(r.text, self.neutral_rubric.text)
        self.assertEqual(r.tags, self.neutral_rubric.tags)
        self.assertEqual(r.meta, self.neutral_rubric.meta)
        self.assertEqual(r.user, self.neutral_rubric.user)
        self.assertIsNot(r.user, self.relative_rubric.user)
        self.assertEqual(r.question, self.neutral_rubric.question)
        self.assertEqual(r.versions, self.neutral_rubric.versions)
        self.assertEqual(r.parameters, self.neutral_rubric.parameters)

    def test_create_relative_rubric(self):
        """Test RubricService.create_rubric() to create a relative rubric."""
        simulated_client_data = {
            "kind": "relative",
            "display_delta": "+3",
            "value": 3,
            "out_of": 0,
            "text": "yuiop",
            "tags": "",
            "meta": "hjklz",
            "username": "Olivia",
            "question": 1,
            "versions": [],
            "parameters": [],
        }
        r = RubricService().create_rubric(simulated_client_data)

        self.assertEqual(r.kind, self.relative_rubric.kind)
        self.assertEqual(r.display_delta, self.relative_rubric.display_delta)
        self.assertEqual(r.text, self.relative_rubric.text)
        self.assertEqual(r.tags, self.relative_rubric.tags)
        self.assertEqual(r.meta, self.relative_rubric.meta)
        self.assertEqual(r.user, self.relative_rubric.user)
        self.assertIsNot(r.user, self.neutral_rubric.user)
        self.assertEqual(r.question, self.relative_rubric.question)
        self.assertEqual(r.versions, self.relative_rubric.versions)
        self.assertEqual(r.parameters, self.relative_rubric.parameters)

    def test_create_absolute_rubric(self):
        """Test RubricService.create_rubric() to create an absolute rubric."""
        simulated_client_data = {
            "kind": "absolute",
            "display_delta": "2 of 5",
            "value": 2,
            "out_of": 5,
            "text": "mnbvc",
            "tags": "",
            "meta": "lkjhg",
            "username": "Liam",
            "question": 3,
            "versions": [],
            "parameters": [],
        }
        r = RubricService().create_rubric(simulated_client_data)

        self.assertEqual(r.kind, self.absolute_rubric.kind)
        self.assertEqual(r.display_delta, self.absolute_rubric.display_delta)
        self.assertEqual(r.text, self.absolute_rubric.text)
        self.assertEqual(r.tags, self.absolute_rubric.tags)
        self.assertEqual(r.meta, self.absolute_rubric.meta)
        self.assertEqual(r.user, self.absolute_rubric.user)
        self.assertIsNot(r.user, self.relative_rubric.user)
        self.assertEqual(r.question, self.absolute_rubric.question)
        self.assertEqual(r.versions, self.absolute_rubric.versions)
        self.assertEqual(r.parameters, self.absolute_rubric.parameters)

    def test_modify_neutral_rubric(self):
        """Test RubricService.modify_rubric() to modify a neural rubric."""
        service = RubricService()
        key = self.modified_neutral_rubric.key

        simulated_client_data = {
            "id": key,
            "kind": "neutral",
            "display_delta": ".",
            "value": 0,
            "out_of": 0,
            "text": "yuiop",
            "tags": "",
            "meta": "hjklz",
            "username": "Olivia",
            "question": 1,
            "versions": [],
            "parameters": [],
        }
        r = service.modify_rubric(key, simulated_client_data)

        self.assertEqual(r.key, self.modified_neutral_rubric.key)
        self.assertEqual(r.kind, self.modified_neutral_rubric.kind)
        self.assertEqual(r.display_delta, self.modified_neutral_rubric.display_delta)

    def test_modify_relative_rubric(self):
        """Test RubricService.modify_rubric() to modify a relative rubric."""
        service = RubricService()
        key = self.modified_relative_rubric.key

        simulated_client_data = {
            "id": key,
            "kind": "relative",
            "display_delta": "+3",
            "value": 3,
            "out_of": 0,
            "text": "yuiop",
            "tags": "",
            "meta": "hjklz",
            "username": "Olivia",
            "question": 1,
            "versions": [],
            "parameters": [],
        }
        r = service.modify_rubric(key, simulated_client_data)

        self.assertEqual(r.key, self.modified_relative_rubric.key)
        self.assertEqual(r.kind, self.modified_relative_rubric.kind)
        self.assertEqual(r.display_delta, self.modified_relative_rubric.display_delta)
        self.assertEqual(r.value, self.modified_relative_rubric.value)
        self.assertEqual(r.user, self.modified_relative_rubric.user)

    def test_modify_absolute_rubric(self):
        """
        Test RubricService.modify_rubric() to modify a relative rubric
        """
        service = RubricService()
        key = self.modified_absolute_rubric.key

        simulated_client_data = {
            "id": key,
            "kind": "absolute",
            "display_delta": "3 of 5",
            "value": 3,
            "out_of": 5,
            "text": "yuiop",
            "tags": "",
            "meta": "hjklz",
            "username": "Olivia",
            "question": 1,
            "versions": [],
            "parameters": [],
        }
        r = service.modify_rubric(key, simulated_client_data)

        self.assertEqual(r.key, self.modified_absolute_rubric.key)
        self.assertEqual(r.kind, self.modified_absolute_rubric.kind)
        self.assertEqual(r.display_delta, self.modified_absolute_rubric.display_delta)
        self.assertEqual(r.value, self.modified_absolute_rubric.value)
        self.assertEqual(r.out_of, self.modified_absolute_rubric.out_of)
        self.assertEqual(r.user, self.modified_absolute_rubric.user)

    def test_modify_rubric_change_kind(self):
        """Test RubricService.modify_rubric(), can change the "kind" of rubrics.

        For each of the three kinds of rubric, we ensure we can change them
        into the other three kinds.  The key should not change.
        """
        user = baker.make(User)
        username = user.username

        for kind in ("absolute", "relative", "neutral"):
            rubric = baker.make(Rubric, user=user, kind=kind)
            key = rubric.key
            d = _rubric_to_dict(rubric)

            d["kind"] = "neutral"
            d["display_delta"] = "."
            d["username"] = username

            r = RubricService().modify_rubric(key, d)
            self.assertEqual(r.key, rubric.key)
            self.assertEqual(r.kind, d["kind"])
            self.assertEqual(r.display_delta, d["display_delta"])

            d["kind"] = "relative"
            d["display_delta"] = "+2"
            d["value"] = 2
            d["username"] = username

            r = RubricService().modify_rubric(key, d)
            self.assertEqual(r.key, rubric.key)
            self.assertEqual(r.kind, d["kind"])
            self.assertEqual(r.display_delta, d["display_delta"])
            self.assertEqual(r.value, d["value"])

            d["kind"] = "absolute"
            d["display_delta"] = "2 of 3"
            d["value"] = 2
            d["out_of"] = 3
            d["username"] = username

            r = RubricService().modify_rubric(key, d)
            self.assertEqual(r.key, rubric.key)
            self.assertEqual(r.kind, d["kind"])
            self.assertEqual(r.display_delta, d["display_delta"])
            self.assertEqual(r.value, d["value"])
            self.assertEqual(r.out_of, d["out_of"])

    def test_rubrics_from_user(self):
        service = RubricService()
        user = baker.make(User)
        rubrics = service.get_rubrics_from_user(user)
        self.assertEqual(rubrics.count(), 0)

        baker.make(Rubric, user=user)
        rubrics = service.get_rubrics_from_user(user)
        self.assertEqual(rubrics.count(), 1)

        baker.make(Rubric, user=user)
        rubrics = service.get_rubrics_from_user(user)
        self.assertEqual(rubrics.count(), 2)

        baker.make(Rubric, user=user)
        rubrics = service.get_rubrics_from_user(user)
        self.assertEqual(rubrics.count(), 3)

    def test_rubrics_from_annotation(self):
        service = RubricService()
        annotation1 = baker.make(Annotation)

        rubrics = service.get_rubrics_from_annotation(annotation1)
        self.assertEqual(rubrics.count(), 0)

        b = baker.make(Rubric)
        b.annotations.add(annotation1)
        b.save()
        rubrics = service.get_rubrics_from_annotation(annotation1)
        self.assertEqual(rubrics.count(), 1)

        b = baker.make(Rubric)
        b.annotations.add(annotation1)
        b.save()
        rubrics = service.get_rubrics_from_annotation(annotation1)
        self.assertEqual(rubrics.count(), 2)

    def test_annotations_from_rubric(self):
        service = RubricService()
        rubric1 = baker.make(Rubric)

        annotations = service.get_annotation_from_rubric(rubric1)
        self.assertEqual(annotations.count(), 0)

        annot1 = baker.make(Annotation, rubric=rubric1)
        rubric1.annotations.add(annot1)
        annotations = service.get_annotation_from_rubric(rubric1)
        self.assertEqual(annotations.count(), 1)

        annot2 = baker.make(Annotation, rubric=rubric1)
        rubric1.annotations.add(annot2)
        annotations = service.get_annotation_from_rubric(rubric1)
        self.assertEqual(annotations.count(), 2)

    def test_rubrics_from_paper(self):
        service = RubricService()
        paper1 = baker.make(Paper, paper_number=1)
        marking_task1 = baker.make(MarkingTask, paper=paper1)
        marking_task2 = baker.make(MarkingTask, paper=paper1)
        annotation1 = baker.make(Annotation, task=marking_task1)
        annotation2 = baker.make(Annotation, task=marking_task2)
        annotation3 = baker.make(Annotation, task=marking_task1)
        annotation4 = baker.make(Annotation, task=marking_task2)

        rubrics = service.get_rubrics_from_paper(paper1)
        self.assertEqual(rubrics.count(), 0)

        rubric1 = baker.make(Rubric)
        rubric1.annotations.add(annotation1)
        rubric1.annotations.add(annotation2)
        rubrics = service.get_rubrics_from_paper(paper1)
        self.assertEqual(rubrics.count(), 2)

        rubric1.annotations.add(annotation3)
        rubric1.annotations.add(annotation4)
        rubrics = service.get_rubrics_from_paper(paper1)
        self.assertEqual(rubrics.count(), 4)
