# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2025 Andrew Rechnitzer
# Copyright (C) 2025 Aidan Murphy
# Copyright (C) 2025 Bryan Tanady

from django.contrib.auth.models import User
from django.test import TestCase
from model_bakery import baker
from rest_framework import serializers

from plom.plom_exceptions import PlomConflict
from plom_server.TestingSupport.utils import config_test
from plom_server.Mark.models.annotations import Annotation
from plom_server.Mark.models.tasks import MarkingTask
from plom_server.Papers.models import Paper
from ..models import Rubric
from ..services import RubricService

# helper fcn private to that service, but useful here
from ..services.rubric_service import _Rubric_to_dict


class RubricServiceTests_exceptions(TestCase):
    """Tests for `Rubric.service.RubricService()` exceptions."""

    @config_test({"test_spec": "demo"})
    def setUp(self) -> None:
        baker.make(User, username="Liam")

    def test_no_user_ValueError(self) -> None:
        rub = {
            "kind": "neutral",
            "value": 0,
            "text": "qwerty",
            "username": "XXX_no_such_user_XXX",
            "question_index": 1,
        }

        with self.assertRaisesRegex(ValueError, "XXX"):
            RubricService.create_rubric(rub)

    def test_no_user_low_level_ValueError(self) -> None:
        """Test ValueError in RubricService.create_rubric().

        This test case checks if the low-level RubricService._create_rubric()
        method raises an ValueError exception when attempting
        to create a rubric with a non-existent user.
        """
        rub = {
            "kind": "neutral",
            "value": 0,
            "text": "qwerty",
            "username": "XXX_no_such_user_XXX",
            "question_index": 1,
        }

        with self.assertRaisesRegex(ValueError, "XXX"):
            RubricService._create_rubric(rub)

    def test_no_user_KeyError(self) -> None:
        """Test KeyError in RubricService.create_rubric().

        This test case checks if RubricService.create_rubric()
        method raises a KeyError when attempting to create a rubric
        without providing the 'username' key in the rubric dictionary.
        """
        rub = {
            "kind": "neutral",
            "value": 0,
            "text": "qwerty",
            "question_index": 1,
        }

        with self.assertRaises(KeyError):
            RubricService.create_rubric(rub)

    def test_no_username_KeyError_lowlevel(self) -> None:
        rub = {
            "kind": "neutral",
            "value": 0,
            "text": "qwerty",
            "question_index": 1,
        }
        with self.assertRaises(KeyError):
            RubricService._create_rubric(rub)

    def test_no_kind_ValidationError(self) -> None:
        """Test for the RubricService.create_rubric() method when 'kind' is invalid.

        This test case checks if the RubricService.create_rubric()
        method raises a serializers.ValidationError when attempting to create
        a rubric with an invalid 'kind' value. The 'kind' value
        is expected to be one of the following: "absolute", "neutral",
        or "relative".
        """
        rub = {
            "kind": "No kind",
            "value": 0,
            "text": "qwerty",
            "username": "Liam",
            "question_index": 1,
        }

        with self.assertRaises(serializers.ValidationError):
            RubricService.create_rubric(rub)

    def test_no_kind_KeyValidationError(self) -> None:
        """Test ValidationError in RubricService.create_rubric().

        This test case checks if the RubricService.create_rubric()
        method raises a serializers.ValidationError when attempting to create a rubric
        without providing the 'kind' key in the rubric dictionary.
        """
        rub = {
            "value": 0,
            "text": "qwerty",
            "username": "Liam",
            "question_index": 1,
        }

        with self.assertRaises(serializers.ValidationError):
            RubricService.create_rubric(rub)

    def test_rubric_absolute_out_of_range(self) -> None:
        rub = {
            "value": 4,
            "out_of": 3,
            "kind": "absolute",
            "text": "qwerty",
            "username": "Liam",
            "question_index": 1,
        }
        # check error thrown when value > out_of
        with self.assertRaisesRegex(serializers.ValidationError, "out of range"):
            RubricService.create_rubric(rub)
        # check if value < 0
        rub["value"] = -2
        with self.assertRaisesRegex(serializers.ValidationError, "out of range"):
            RubricService.create_rubric(rub)
        # check if out_of > max_mark
        rub["value"] = 3
        rub["out_of"] = 99
        with self.assertRaisesRegex(serializers.ValidationError, "out of range"):
            RubricService.create_rubric(rub)

    def test_create_rubric_should_not_have_existing_rid(self) -> None:
        rub = {
            "kind": "neutral",
            "value": 0,
            "text": "qwerty",
            "username": "Liam",
            "question_index": 1,
            "rid": 42,
        }
        with self.assertRaisesRegex(serializers.ValidationError, 'not have a "rid"'):
            RubricService.create_rubric(rub)


class RubricServiceTests_extra_validation(TestCase):
    """Tests for various validation routines, currently those not model-integrated."""

    @config_test({"test_spec": "demo"})
    def setUp(self) -> None:
        self.user_liam = baker.make(User, username="Liam")

    def test_create_rubric_invalid_value(self) -> None:
        rub = {
            "kind": "relative",
            "value": -999,
            "text": "qwerty",
            "username": "Liam",
            "question_index": 1,
        }
        with self.assertRaisesRegex(serializers.ValidationError, "value"):
            RubricService.create_rubric(rub)

    def test_create_rubric_versions_invalid(self) -> None:
        for bad_versions in ("[1, 2]", [1, 1.2], "1, 1.2", "1, sth", "abc"):
            rub = {
                "kind": "neutral",
                "value": 0,
                "text": "qwerty",
                "username": "Liam",
                "question_index": 1,
                "versions": bad_versions,
            }
            with self.assertRaisesRegex(serializers.ValidationError, "versions"):
                RubricService.create_rubric(rub)

    def test_create_rubric_versions_out_of_range(self) -> None:
        for oor_versions in ("-1", "999", "-1, 1", "-1, 999"):
            rub = {
                "kind": "neutral",
                "value": 0,
                "text": "qwerty",
                "username": "Liam",
                "question_index": 1,
                "versions": oor_versions,
            }
            with self.assertRaisesRegex(serializers.ValidationError, "out of range"):
                RubricService.create_rubric(rub)

    def test_create_rubric_valid_parameters(self) -> None:
        for good_params in (
            [],
            [["{param1}", ["bar", "baz"]]],
            [("{param1}", ["bar", "baz"]), ("<param2>", ("foo", "foz"))],
        ):
            rub = {
                "kind": "neutral",
                "value": 0,
                "text": "qwerty",
                "username": "Liam",
                "question_index": 1,
                "parameters": good_params,
            }
            RubricService.create_rubric(rub)

    def test_create_rubric_invalid_parameters(self) -> None:
        for bad_params in (
            "[]",
            [["{param1}", ["bar"]]],
            [["foo", "bar", "baz"]],
            [["foo", "bar"]],
            [["foo", [1, 2]]],
            [[42, ["bar", "baz"]]],
        ):
            rub = {
                "kind": "neutral",
                "value": 0,
                "text": "qwerty",
                "username": "Liam",
                "question_index": 1,
                "parameters": bad_params,
            }
            with self.assertRaises(serializers.ValidationError):
                RubricService.create_rubric(rub)


class RubricServiceTests(TestCase):
    """Tests for `Rubric.service.RubricService()`."""

    @config_test({"test_spec": "demo"})
    def setUp(self) -> None:
        user1: User = baker.make(User, username="Liam")
        user2: User = baker.make(User, username="Olivia")
        self.user_liam = user1
        self.user_olivia = user2

        self.neutral_rubric = baker.make(
            Rubric,
            kind="neutral",
            display_delta=".",
            value=0.0,
            out_of=0.0,
            text="qwert",
            question_index=1,
            user=user1,
            tags="",
            meta="asdfg",
            versions="",
            parameters=[],
        )

        self.modified_neutral_rubric = baker.make(
            Rubric,
            kind="neutral",
            display_delta=".",
            value=0.0,
            out_of=0.0,
            text="yuiop",
            question_index=1,
            user=user2,
            tags="",
            meta="hjklz",
            versions="",
            parameters=[],
        )

        self.relative_rubric = baker.make(
            Rubric,
            kind="relative",
            display_delta="+2.0",
            value=2.0,
            out_of=0.0,
            text="yuiop",
            question_index=1,
            user=user2,
            tags="",
            meta="hjklz",
            versions="",
            parameters=[],
        )

        self.modified_relative_rubric = baker.make(
            Rubric,
            kind="relative",
            display_delta="+3.0",
            value=3.0,
            user=user2,
        )

        self.absolute_rubric = baker.make(
            Rubric,
            kind="absolute",
            display_delta="2.0 of 5.0",
            value=2.0,
            out_of=5.0,
            text="mnbvc",
            question_index=3,
            user=user1,
            tags="",
            meta="lkjhg",
            versions="",
            parameters=[],
        )

        self.modified_absolute_rubric = baker.make(
            Rubric,
            kind="absolute",
            display_delta="3.0 of 5.0",
            value=3.0,
            out_of=5.0,
            user=user2,
        )

        return super().setUp()

    def test_create_neutral_rubric(self) -> None:
        simulated_client_data = {
            "kind": "neutral",
            "display_delta": ".",
            "value": 0.0,
            "out_of": 0.0,
            "text": "qwert",
            "tags": "",
            "meta": "asdfg",
            "username": "Liam",
            "question_index": 1,
            "parameters": [],
        }
        r = RubricService._create_rubric(simulated_client_data)

        self.assertEqual(r.kind, self.neutral_rubric.kind)
        self.assertEqual(r.display_delta, self.neutral_rubric.display_delta)
        self.assertEqual(r.text, self.neutral_rubric.text)
        self.assertEqual(r.tags, self.neutral_rubric.tags)
        self.assertEqual(r.meta, self.neutral_rubric.meta)
        self.assertEqual(r.user, self.neutral_rubric.user)
        self.assertIsNot(r.user, self.relative_rubric.user)
        self.assertEqual(r.question_index, self.neutral_rubric.question_index)
        self.assertEqual(r.versions, self.neutral_rubric.versions)
        self.assertEqual(r.parameters, self.neutral_rubric.parameters)

    def test_create_relative_rubric(self) -> None:
        simulated_client_data = {
            "kind": "relative",
            "display_delta": "+2.0",
            "value": 2.0,
            "out_of": 0.0,
            "text": "yuiop",
            "tags": "",
            "meta": "hjklz",
            "username": "Olivia",
            "question_index": 1,
            "parameters": [],
        }
        r = RubricService._create_rubric(simulated_client_data)

        self.assertEqual(r.kind, self.relative_rubric.kind)
        self.assertEqual(r.display_delta, self.relative_rubric.display_delta)
        self.assertEqual(r.text, self.relative_rubric.text)
        self.assertEqual(r.tags, self.relative_rubric.tags)
        self.assertEqual(r.meta, self.relative_rubric.meta)
        self.assertEqual(r.user, self.relative_rubric.user)
        self.assertIsNot(r.user, self.neutral_rubric.user)
        self.assertEqual(r.question_index, self.relative_rubric.question_index)
        self.assertEqual(r.versions, self.relative_rubric.versions)
        self.assertEqual(r.parameters, self.relative_rubric.parameters)

    def test_create_absolute_rubric(self) -> None:
        simulated_client_data = {
            "kind": "absolute",
            "display_delta": "2.0 of 5.0",
            "value": 2.0,
            "out_of": 5.0,
            "text": "mnbvc",
            "tags": "",
            "meta": "lkjhg",
            "username": "Liam",
            "question_index": 3,
            "parameters": [],
        }
        r = RubricService._create_rubric(simulated_client_data)

        self.assertEqual(r.kind, self.absolute_rubric.kind)
        self.assertEqual(r.display_delta, self.absolute_rubric.display_delta)
        self.assertEqual(r.text, self.absolute_rubric.text)
        self.assertEqual(r.tags, self.absolute_rubric.tags)
        self.assertEqual(r.meta, self.absolute_rubric.meta)
        self.assertEqual(r.user, self.absolute_rubric.user)
        self.assertIsNot(r.user, self.relative_rubric.user)
        self.assertEqual(r.question_index, self.absolute_rubric.question_index)
        self.assertEqual(r.versions, self.absolute_rubric.versions)
        self.assertEqual(r.parameters, self.absolute_rubric.parameters)

    def test_create_rubric_makes_dict(self) -> None:
        simulated_client_data = {
            "kind": "neutral",
            "value": 0.0,
            "text": "qwerty",
            "username": "Olivia",
            "question_index": 1,
        }
        r = RubricService.create_rubric(simulated_client_data)
        assert isinstance(r, dict)

    def test_modify_neutral_rubric(self) -> None:
        """Test RubricService.modify_rubric() to modify a neural rubric."""
        rid = self.modified_neutral_rubric.rid

        simulated_client_data = {
            "rid": rid,
            "kind": "neutral",
            "display_delta": ".",
            "value": 0.0,
            "out_of": 0.0,
            "text": "yuiop",
            "tags": "",
            "meta": "hjklz",
            "username": "Olivia",
            "question_index": 1,
            "parameters": [],
        }
        r = RubricService.modify_rubric(rid, simulated_client_data)

        self.assertEqual(r["rid"], self.modified_neutral_rubric.rid)
        self.assertEqual(r["kind"], self.modified_neutral_rubric.kind)
        self.assertEqual(r["display_delta"], self.modified_neutral_rubric.display_delta)

    def test_modify_relative_rubric(self) -> None:
        """Test RubricService.modify_rubric() to modify a relative rubric."""
        rid = self.modified_relative_rubric.rid

        simulated_client_data = {
            "rid": rid,
            "kind": "relative",
            "display_delta": "+3.0",
            "value": 3.0,
            "out_of": 0.0,
            "text": "yuiop",
            "tags": "",
            "meta": "hjklz",
            "username": "Olivia",
            "question_index": 1,
            "parameters": [],
        }
        r = RubricService.modify_rubric(rid, simulated_client_data)

        self.assertEqual(r["rid"], self.modified_relative_rubric.rid)
        self.assertEqual(r["kind"], self.modified_relative_rubric.kind)
        self.assertEqual(
            r["display_delta"], self.modified_relative_rubric.display_delta
        )
        self.assertEqual(r["value"], self.modified_relative_rubric.value)
        self.assertEqual(r["username"], self.modified_relative_rubric.user.username)

    def test_modify_absolute_rubric(self) -> None:
        """Test RubricService.modify_rubric() to modify a relative rubric."""
        rid = self.modified_absolute_rubric.rid

        simulated_client_data = {
            "rid": rid,
            "kind": "absolute",
            "display_delta": "3.0 of 5.0",
            "value": 3.0,
            "out_of": 5.0,
            "text": "yuiop",
            "tags": "",
            "meta": "hjklz",
            "username": "Olivia",
            "question_index": 1,
            "parameters": [],
        }
        r = RubricService.modify_rubric(rid, simulated_client_data)

        self.assertEqual(r["rid"], self.modified_absolute_rubric.rid)
        self.assertEqual(r["kind"], self.modified_absolute_rubric.kind)
        self.assertEqual(
            r["display_delta"], self.modified_absolute_rubric.display_delta
        )
        self.assertEqual(r["value"], self.modified_absolute_rubric.value)
        self.assertEqual(r["out_of"], self.modified_absolute_rubric.out_of)
        self.assertEqual(r["username"], self.modified_absolute_rubric.user.username)

    def test_modify_absolute_rubric_change_value_autogen_display(self) -> None:
        rid = self.modified_absolute_rubric.rid

        simulated_client_data = {
            "rid": rid,
            "kind": "absolute",
            "value": 2,
            "out_of": 3,
            "text": "yuiop",
            "username": "Olivia",
            "question_index": 1,
        }
        r = RubricService.modify_rubric(rid, simulated_client_data)
        self.assertEqual(r["display_delta"], "2 of 3")

    def test_modify_absolute_rubric_change_value_no_autogen_display(self) -> None:
        rid = self.modified_absolute_rubric.rid

        simulated_client_data = {
            "rid": rid,
            "kind": "absolute",
            "value": 2,
            "out_of": 3,
            "display_delta": "2.00 of 3.00",
            "text": "yuiop",
            "username": "Olivia",
            "question_index": 1,
        }
        r = RubricService.modify_rubric(rid, simulated_client_data)
        self.assertEqual(r["display_delta"], "2.00 of 3.00")

    def test_modify_rubric_change_kind(self) -> None:
        """Test RubricService.modify_rubric(), can change the "kind" of rubrics.

        For each of the three kinds of rubric, we ensure we can change them
        into the other three kinds.  The rid should not change.
        """
        user: User = baker.make(User)
        username = user.username

        for kind in ("absolute", "relative", "neutral"):
            rubric = baker.make(
                Rubric, user=user, kind=kind, latest=True, question_index=1
            )
            rid = rubric.rid
            d = _Rubric_to_dict(rubric)

            d["kind"] = "neutral"
            d["display_delta"] = "."
            d["username"] = username

            r = RubricService.modify_rubric(rid, d)
            self.assertEqual(r["rid"], rubric.rid)
            self.assertEqual(r["kind"], d["kind"])
            self.assertEqual(r["display_delta"], d["display_delta"])

            d = r
            d["kind"] = "relative"
            d["display_delta"] = "+2"
            d["value"] = 2.0
            d["username"] = username

            r = RubricService.modify_rubric(rid, d)
            self.assertEqual(r["rid"], rubric.rid)
            self.assertEqual(r["kind"], d["kind"])
            self.assertEqual(r["display_delta"], d["display_delta"])
            self.assertEqual(r["value"], d["value"])

            d = r
            d["kind"] = "absolute"
            d["display_delta"] = "2 of 3"
            d["value"] = 2.0
            d["out_of"] = 3.0
            d["username"] = username

            r = RubricService.modify_rubric(rid, d)
            self.assertEqual(r["rid"], rubric.rid)
            self.assertEqual(r["kind"], d["kind"])
            self.assertEqual(r["display_delta"], d["display_delta"])
            self.assertEqual(r["value"], d["value"])
            self.assertEqual(r["out_of"], d["out_of"])

    def test_rubrics_created_by_user(self) -> None:
        user: User = baker.make(User)
        rubrics = RubricService.get_rubrics_created_by_user(user)
        self.assertEqual(rubrics.count(), 0)

        baker.make(Rubric, user=user)
        rubrics = RubricService.get_rubrics_created_by_user(user)
        self.assertEqual(rubrics.count(), 1)

        baker.make(Rubric, user=user)
        rubrics = RubricService.get_rubrics_created_by_user(user)
        self.assertEqual(rubrics.count(), 2)

        baker.make(Rubric, user=user)
        rubrics = RubricService.get_rubrics_created_by_user(user)
        self.assertEqual(rubrics.count(), 3)

    def test_rubrics_from_annotation(self) -> None:
        annotation1 = baker.make(Annotation)

        rubrics = RubricService.get_rubrics_from_annotation(annotation1)
        self.assertEqual(rubrics.count(), 0)

        b = baker.make(Rubric)
        b.annotations.add(annotation1)
        b.save()
        rubrics = RubricService.get_rubrics_from_annotation(annotation1)
        self.assertEqual(rubrics.count(), 1)

        b = baker.make(Rubric)
        b.annotations.add(annotation1)
        b.save()
        rubrics = RubricService.get_rubrics_from_annotation(annotation1)
        self.assertEqual(rubrics.count(), 2)

    def test_annotations_from_rubric(self) -> None:
        rubric1 = baker.make(Rubric)

        annotations = RubricService.get_annotations_from_rubric(rubric1)
        self.assertEqual(annotations.count(), 0)

        annot1 = baker.make(Annotation, rubric=rubric1)
        rubric1.annotations.add(annot1)
        annotations = RubricService.get_annotations_from_rubric(rubric1)
        self.assertEqual(annotations.count(), 1)

        annot2 = baker.make(Annotation, rubric=rubric1)
        rubric1.annotations.add(annot2)
        annotations = RubricService.get_annotations_from_rubric(rubric1)
        self.assertEqual(annotations.count(), 2)

    def test_rubrics_from_paper(self) -> None:
        paper1 = baker.make(Paper, paper_number=1)
        marking_task1 = baker.make(MarkingTask, paper=paper1)
        marking_task2 = baker.make(MarkingTask, paper=paper1)
        annotation1 = baker.make(Annotation, task=marking_task1)
        annotation2 = baker.make(Annotation, task=marking_task2)
        annotation3 = baker.make(Annotation, task=marking_task1)
        annotation4 = baker.make(Annotation, task=marking_task2)

        rubrics = RubricService.get_rubrics_from_paper(paper1)
        self.assertEqual(rubrics.count(), 0)

        rubric1 = baker.make(Rubric)
        rubric1.annotations.add(annotation1)
        rubric1.annotations.add(annotation2)
        rubrics = RubricService.get_rubrics_from_paper(paper1)
        self.assertEqual(rubrics.count(), 2)

        rubric1.annotations.add(annotation3)
        rubric1.annotations.add(annotation4)
        rubrics = RubricService.get_rubrics_from_paper(paper1)
        self.assertEqual(rubrics.count(), 4)

    def test_modify_rubric_wrong_revision(self) -> None:
        rub = {
            "kind": "neutral",
            "text": "qwerty",
            "username": "Liam",
            "question_index": 1,
            "revision": 10,
        }
        r = RubricService.create_rubric(rub)
        rid = r["rid"]

        # ok to change if revision matches
        rub.update({"text": "Changed"})
        RubricService.modify_rubric(rid, rub)

        # but its an error if the revision does not match
        rub.update({"revision": 0})
        with self.assertRaises(PlomConflict):
            RubricService.modify_rubric(rid, rub)

    def test_modify_absolute_rubric_change_value_invalid(self) -> None:
        rid = self.modified_absolute_rubric.rid

        simulated_client_data = {
            "rid": rid,
            "kind": "absolute",
            "value": 4,
            "out_of": 3,
            "text": "yuiop",
            "username": "Olivia",
            "question_index": 1,
        }
        with self.assertRaisesRegex(serializers.ValidationError, "out of range"):
            RubricService.modify_rubric(rid, simulated_client_data)
        simulated_client_data["value"] = -2
        with self.assertRaisesRegex(serializers.ValidationError, "out of range"):
            RubricService.modify_rubric(rid, simulated_client_data)
        simulated_client_data["value"] = 99
        with self.assertRaisesRegex(serializers.ValidationError, "out of range"):
            RubricService.modify_rubric(rid, simulated_client_data)
        simulated_client_data["value"] = 4
        simulated_client_data["out_of"] = 99
        with self.assertRaisesRegex(serializers.ValidationError, "out of range"):
            RubricService.modify_rubric(rid, simulated_client_data)

    def test_modify_absolute_rubric_change_value_nonnumeric(self) -> None:
        rid = self.modified_absolute_rubric.rid

        simulated_client_data = {
            "rid": rid,
            "kind": "absolute",
            "value": "forty two",
            "display_delta": "forty two",
            "out_of": 3,
            "text": "yuiop",
            "username": "Olivia",
            "question_index": 1,
        }
        with self.assertRaisesRegex(serializers.ValidationError, "value.*convertible"):
            RubricService.modify_rubric(rid, simulated_client_data)

    def test_modify_absolute_rubric_change_out_of_nonnumeric(self) -> None:
        rid = self.modified_absolute_rubric.rid

        simulated_client_data = {
            "rid": rid,
            "kind": "absolute",
            "value": 3,
            "display_delta": "3",
            "out_of": "four",
            "text": "yuiop",
            "username": "Olivia",
            "question_index": 1,
        }
        with self.assertRaisesRegex(serializers.ValidationError, "out of.*convertible"):
            RubricService.modify_rubric(rid, simulated_client_data)

    def test_rubrics_get_as_dicts(self) -> None:
        rubrics = RubricService().get_rubrics_as_dicts()
        self.assertEqual(len(rubrics), RubricService().get_rubric_count())
        for r in rubrics:
            assert isinstance(r, dict)

    def test_modify_autodetect_major_edit_on_value_change(self) -> None:
        data = _Rubric_to_dict(self.absolute_rubric)
        rid = data["rid"]
        data["value"] += 1
        new = RubricService.modify_rubric(rid, data, is_minor_change=None)
        self.assertEqual(new["revision"], data["revision"] + 1)

    def test_modify_autodetect_major_edit_on_kind_change(self) -> None:
        data = _Rubric_to_dict(self.neutral_rubric)
        rid = data["rid"]
        data["value"] = 1
        data["kind"] = "relative"
        data.pop("out_of")
        new = RubricService.modify_rubric(rid, data, is_minor_change=None)
        self.assertEqual(new["revision"], data["revision"] + 1)

    def test_modify_autodetect_major_edit_on_out_of_change(self) -> None:
        data = _Rubric_to_dict(self.absolute_rubric)
        rid = data["rid"]
        data["out_of"] -= 1
        new = RubricService.modify_rubric(rid, data, is_minor_change=None)
        self.assertEqual(new["revision"], data["revision"] + 1)

    def test_modify_autodetect_major_edit_on_change_question(self) -> None:
        data = _Rubric_to_dict(self.absolute_rubric)
        rid = data["rid"]
        current_qidx = data["question_index"]
        assert current_qidx != 2, "test invalid unless we change the question index"
        data["question_index"] = 2
        new = RubricService.modify_rubric(rid, data, is_minor_change=None)
        self.assertEqual(new["revision"], data["revision"] + 1)

    def test_modify_autodetect_minor_edit_on_tag_change(self) -> None:
        data = _Rubric_to_dict(self.absolute_rubric)
        rid = data["rid"]
        data["tags"] = "new_tag"
        new = RubricService.modify_rubric(rid, data, is_minor_change=None)
        self.assertEqual(new["revision"], data["revision"])

    def test_modify_force_minor_than_major_change_text(self) -> None:
        data = _Rubric_to_dict(self.absolute_rubric)
        rid = data["rid"]
        data["text"] = data["text"] + "changing text"
        new1 = RubricService.modify_rubric(rid, data, is_minor_change=True)
        # minor changes leaves revision unchanged and increases subrevision
        self.assertEqual(new1["revision"], data["revision"])
        self.assertEqual(new1["subrevision"], data["subrevision"] + 1)

        # a subsequent major change
        new1["text"] = new1["text"] + "more changes"
        new2 = RubricService.modify_rubric(rid, new1, is_minor_change=False)
        # major change increases revision and resets subrevision
        self.assertEqual(new2["revision"], new1["revision"] + 1)
        self.assertEqual(new2["subrevision"], 0)

    def test_modify_force_minor_change_value(self) -> None:
        data = _Rubric_to_dict(self.absolute_rubric)
        rid = data["rid"]
        data["value"] += 1
        new1 = RubricService.modify_rubric(rid, data, is_minor_change=True)
        self.assertEqual(new1["revision"], data["revision"])
        self.assertEqual(new1["subrevision"], data["subrevision"] + 1)

        new1["value"] += 1
        new2 = RubricService.modify_rubric(rid, new1, is_minor_change=False)
        self.assertEqual(new2["revision"], new1["revision"] + 1)
        self.assertEqual(new2["subrevision"], 0)
