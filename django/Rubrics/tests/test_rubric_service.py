# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

from django.contrib.auth.models import User
from django.test import TestCase
from model_bakery import baker

from Rubrics.models import NeutralRubric, RelativeRubric
from Rubrics.services import RubricService


class RubricServiceTests(TestCase):
    """
    Tests for Rubric.service.rubric_service()
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

        return super().setUp()

    def test_create_neutral_rubric(self):
        rs = RubricService()

        simulated_user_input = {
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

        # ntdr -> neutral_test_data_rubric
        ntdr = rs.create_rubric(simulated_user_input)

        # kind
        self.assertEqual(ntdr.kind, self.neutral_rubric.kind)

        # display_delta
        self.assertEqual(ntdr.display_delta, self.neutral_rubric.display_delta)

        # text
        self.assertEqual(ntdr.text, self.neutral_rubric.text)

        # tags -> client said "mostly future use" return empty
        self.assertFalse(ntdr.tags)
        self.assertEqual(ntdr.tags, self.neutral_rubric.tags)

        # meta
        self.assertEqual(ntdr.meta, self.neutral_rubric.meta)

        # user
        self.assertEqual(ntdr.user, self.neutral_rubric.user)
        self.assertIsNot(ntdr.user, self.relative_rubric.user)

        # question
        self.assertEqual(ntdr.question, self.neutral_rubric.question)

        # version
        self.assertEqual(ntdr.versions, self.neutral_rubric.versions)

        # parameters
        self.assertEqual(ntdr.parameters, self.neutral_rubric.parameters)

    def test_create_relative_rubric(self):
        rs = RubricService()

        simulated_user_input = {
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

        # rtdr -> relative_test_data_rubric
        rtdr = rs.create_rubric(simulated_user_input)

        # kind
        self.assertEqual(rtdr.kind, self.relative_rubric.kind)

        # display_delta
        self.assertEqual(rtdr.display_delta, self.relative_rubric.display_delta)

        # text
        self.assertEqual(rtdr.text, self.relative_rubric.text)

        # tags -> client said "mostly future use" return empty
        self.assertFalse(rtdr.tags)
        self.assertEqual(rtdr.tags, self.relative_rubric.tags)

        # meta
        self.assertEqual(rtdr.meta, self.relative_rubric.meta)

        # user
        self.assertEqual(rtdr.user, self.relative_rubric.user)
        self.assertIsNot(rtdr.user, self.neutral_rubric.user)

        # question
        self.assertEqual(rtdr.question, self.relative_rubric.question)

        # version
        self.assertEqual(rtdr.versions, self.relative_rubric.versions)

        # parameters
        self.assertEqual(rtdr.parameters, self.relative_rubric.parameters)

    def test_modify_neutral_rubric(self):
        pass

    def test_modify_relative_rubric(self):
        pass

    def test_modify_neutral_to_relative_rubric(self):
        pass

    def test_modify_relative_to_neutral_rubric(self):
        pass