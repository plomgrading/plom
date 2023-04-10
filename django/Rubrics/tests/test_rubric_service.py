# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu

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

        rs = RubricService()

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

        # ntdr -> neutral_test_data_rubric
        ntdr = rs.create_rubric(simulated_client_data)

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
        """
        Test RubricService.create_rubric() to create a relative rubric
        """

        rs = RubricService()

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

        # rtdr -> relative_test_data_rubric
        rtdr = rs.create_rubric(simulated_client_data)

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
        """
        Test RubricService.modify_rubric() to modify a neural rubric
        """

        rs = RubricService()
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

        # mntdr -> modified_neutral_test_data_rubric
        mntdr = rs.modify_rubric(key, simulated_client_data)

        self.assertEqual(mntdr.key, self.modified_neutral_rubric.key)
        self.assertEqual(mntdr.kind, self.modified_neutral_rubric.kind)
        self.assertEqual(
            mntdr.display_delta, self.modified_neutral_rubric.display_delta
        )

    def test_modify_relative_rubric(self):
        """
        Test RubricService.modify_rubric() to modify a relative rubric
        """

        rs = RubricService()
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

        # mrtdr -> modified_relative_test_data_rubric
        mrtdr = rs.modify_rubric(key, simulated_client_data)

        self.assertEqual(mrtdr.key, self.modified_relative_rubric.key)
        self.assertEqual(mrtdr.kind, self.modified_relative_rubric.kind)
        self.assertEqual(
            mrtdr.display_delta, self.modified_relative_rubric.display_delta
        )

    def test_modify_neutral_to_relative_rubric(self):
        """
        Test RubricService.modify_rubric() to modify a neutral rubric
        to a relative rubric
        """

        rs = RubricService()
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

        # mntrr -> modified_neutral_to_relative_rubric
        mntrr = rs.modify_rubric(key, simulated_client_data)

        self.assertEqual(mntrr.key, self.neutral_to_relative_rubric.key)
        self.assertEqual(mntrr.kind, self.neutral_to_relative_rubric.kind)
        self.assertEqual(
            mntrr.display_delta, self.neutral_to_relative_rubric.display_delta
        )
        self.assertEqual(mntrr.user, self.neutral_to_relative_rubric.user)

    def test_modify_relative_to_neutral_rubric(self):
        """
        Test RubricService.modify_rubric() to modify a relative rubric
        to a neutral rubric
        """

        rs = RubricService()
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

        # mrtnr -> modified_relative_to_neutral_rubric
        mrtnr = rs.modify_rubric(key, simulated_client_data)

        self.assertEqual(mrtnr.key, self.relative_to_neutral_rubric.key)
        self.assertEqual(mrtnr.kind, self.relative_to_neutral_rubric.kind)
        self.assertEqual(
            mrtnr.display_delta, self.relative_to_neutral_rubric.display_delta
        )
        self.assertEqual(mrtnr.user, self.relative_to_neutral_rubric.user)
