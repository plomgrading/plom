# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.contrib.auth.models import User
from django.test import TestCase
from model_bakery import baker

from Rubrics.models import NeutralRubric, RelativeRubric
from Rubrics.services import RubricService


class RubricServiceTests(TestCase):
    """
    Tests for Rubric.service.RubricService()
    """

    def setUp(self):
        self.user = baker.make(User, username="Liam")
        self.user2 = baker.make(User, username="Olivia")

        self.neutral_rubric = baker.make(
            NeutralRubric,
            kind="neutral",
            display_delta=".",
            value=0,
            out_of=0,
            text="qwert",
            question=1,
            user=self.user,
            tags="",
            meta="asdfg",
            versions=[],
            parameters=[],
        )

        self.modified_neutral_rubric = baker.make(
            NeutralRubric,
            kind="neutral",
            display_delta=".",
            value=0,
            out_of=0,
            text="yuiop",
            question=1,
            user=self.user2,
            tags="",
            meta="hjklz",
            versions=[],
            parameters=[],
        )

        self.relative_rubric = baker.make(
            RelativeRubric,
            kind="relative",
            display_delta="+3",
            value=3,
            out_of=0,
            text="yuiop",
            question=1,
            user=self.user2,
            tags="",
            meta="hjklz",
            versions=[],
            parameters=[],
        )

        self.modified_relative_rubric = baker.make(
            RelativeRubric,
            kind="relative",
            display_delta="+2",
            value=2,
            out_of=0,
            text="qwert",
            question=1,
            user=self.user,
            tags="",
            meta="asdfg",
            versions=[],
            parameters=[],
        )

        self.neutral_to_relative_rubric = baker.make(
            RelativeRubric,
            key=self.modified_neutral_rubric.key,
            kind="relative",
            display_delta="+2",
            user=self.user,
        )

        self.relative_to_neutral_rubric = baker.make(
            NeutralRubric,
            key=self.modified_relative_rubric.key,
            kind="neutral",
            display_delta=".",
            user=self.user2,
        )

        return super().setUp()

    def test_create_neutral_rubric(self):
        """
        Test RubricService.create_rubric() to create a neural rubric
        """
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

        # Issue #2661
        # tags -> client said "mostly future use" return empty
        self.assertFalse(r.tags)
        self.assertEqual(r.tags, self.neutral_rubric.tags)

        self.assertEqual(r.meta, self.neutral_rubric.meta)
        self.assertEqual(r.user, self.neutral_rubric.user)
        self.assertIsNot(r.user, self.relative_rubric.user)
        self.assertEqual(r.question, self.neutral_rubric.question)
        self.assertEqual(r.versions, self.neutral_rubric.versions)
        self.assertEqual(r.parameters, self.neutral_rubric.parameters)

    def test_create_relative_rubric(self):
        """
        Test RubricService.create_rubric() to create a relative rubric
        """
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

        # Issue #2661
        # tags -> client said "mostly future use" return empty
        self.assertFalse(r.tags)
        self.assertEqual(r.tags, self.relative_rubric.tags)

        self.assertEqual(r.meta, self.relative_rubric.meta)
        self.assertEqual(r.user, self.relative_rubric.user)
        self.assertIsNot(r.user, self.neutral_rubric.user)
        self.assertEqual(r.question, self.relative_rubric.question)
        self.assertEqual(r.versions, self.relative_rubric.versions)
        self.assertEqual(r.parameters, self.relative_rubric.parameters)

    def test_modify_neutral_rubric(self):
        """
        Test RubricService.modify_rubric() to modify a neural rubric
        """
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
        """
        Test RubricService.modify_rubric() to modify a relative rubric
        """
        key = self.modified_relative_rubric.key
        simulated_client_data = {
            "id": key,
            "kind": "relative",
            "display_delta": "+2",
            "value": 2,
            "out_of": 0,
            "text": "qwert",
            "tags": "",
            "meta": "asdfg",
            "username": "Liam",
            "question": 1,
            "versions": [],
            "parameters": [],
        }
        r = RubricService().modify_rubric(key, simulated_client_data)

        self.assertEqual(r.key, self.modified_relative_rubric.key)
        self.assertEqual(r.kind, self.modified_relative_rubric.kind)
        self.assertEqual(r.display_delta, self.modified_relative_rubric.display_delta)

    def test_modify_neutral_to_relative_rubric(self):
        """
        Test RubricService.modify_rubric() to modify a neutral rubric
        to a relative rubric
        """
        key = self.modified_neutral_rubric.key
        simulated_client_data = {
            "id": key,
            "kind": "relative",
            "display_delta": "+2",
            "value": 2,
            "out_of": 0,
            "text": "qwert",
            "tags": "",
            "meta": "asdfg",
            "username": "Liam",
            "question": 1,
            "versions": [],
            "parameters": [],
        }
        r = RubricService().modify_rubric(key, simulated_client_data)

        self.assertEqual(r.key, self.neutral_to_relative_rubric.key)
        self.assertEqual(r.kind, self.neutral_to_relative_rubric.kind)
        self.assertEqual(r.display_delta, self.neutral_to_relative_rubric.display_delta)
        self.assertEqual(r.user, self.neutral_to_relative_rubric.user)

    def test_modify_relative_to_neutral_rubric(self):
        """
        Test RubricService.modify_rubric() to modify a relative rubric
        to a neutral rubric
        """
        key = self.modified_relative_rubric.key
        simulated_client_data = {
            "id": key,
            "kind": "neutral",
            "display_delta": ".",
            "value": 0,
            "out_of": 0,
            "text": "qwert",
            "tags": "",
            "meta": "asdfg",
            "username": "Olivia",
            "question": 1,
            "versions": [],
            "parameters": [],
        }
        r = RubricService().modify_rubric(key, simulated_client_data)

        self.assertEqual(r.key, self.relative_to_neutral_rubric.key)
        self.assertEqual(r.kind, self.relative_to_neutral_rubric.kind)
        self.assertEqual(r.display_delta, self.relative_to_neutral_rubric.display_delta)
        self.assertEqual(r.user, self.relative_to_neutral_rubric.user)
