# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024-2025 Aidan Murphy

from django.test import TestCase
from django.core.exceptions import MultipleObjectsReturned
from django.contrib.auth.models import User
from model_bakery import baker

from plom_server.Papers.models import Paper, QuestionPage
from plom_server.Rubrics.models import Rubric

from plom.plom_exceptions import PlomConflict, PlomInconsistentRubric
from ..services import MarkingTaskService
from ..models import MarkingTask, AnnotationImage
from ..services.annotations import _create_new_annotation_in_database
from plom_server.Papers.services import SpecificationService


class MiscIncomingAnnotationsTests(TestCase):
    def setUp(self) -> None:
        spec_dict = {
            "idPage": 1,
            "numberOfVersions": 2,
            "numberOfPages": 6,
            "totalMarks": 10,
            "numberOfQuestions": 2,
            "name": "papers_demo",
            "longName": "Papers Test",
            "doNotMarkPages": [2, 5, 6],
            "question": [
                {"pages": [3], "mark": 5},
                {"pages": [4], "mark": 5},
            ],
        }
        SpecificationService.install_spec_from_dict(spec_dict)
        user1: User = baker.make(User, username="User1")
        self.rubric1_on_3 = baker.make(
            Rubric,
            kind="relative",
            display_delta="+1/3",
            value=1 / 3,
            text="test +1/3",
            question_index=1,
            user=user1,
        )
        self.rubric1_on_3_poor_rounding = baker.make(
            Rubric,
            kind="relative",
            display_delta="+1/3",
            value=0.33,
            text="test +1/3",
            question_index=1,
            user=user1,
        )
        self.rubric3 = baker.make(
            Rubric,
            kind="relative",
            display_delta="+3",
            value=3.0,
            text="test +3",
            question_index=1,
            user=user1,
        )
        self.rubric_q2 = baker.make(
            Rubric,
            kind="relative",
            display_delta="+1",
            value=1.0,
            text="test +1 wrong question",
            question_index=2,
            user=user1,
        )
        return super().setUp()

    # some existing rests imported here and split into multiple parts
    def test_marking_outdated(self) -> None:
        mts = MarkingTaskService()
        self.assertRaises(ValueError, mts.set_paper_marking_task_outdated, 1, 1)
        baker.make(Paper, paper_number=1)
        mts.set_paper_marking_task_outdated(1, 1)  # confirm no errors raised

    def test_marking_outdated2(self) -> None:
        mts = MarkingTaskService()
        paper1 = baker.make(Paper, paper_number=1)

        user0: User = baker.make(User)
        baker.make(
            MarkingTask,
            code="0001g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper1,
            question_index=1,
        )
        baker.make(
            MarkingTask,
            code="0001g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper1,
            question_index=1,
        )
        self.assertRaises(
            MultipleObjectsReturned, mts.set_paper_marking_task_outdated, 1, 1
        )

    def test_marking_outdated3(self) -> None:
        """Use a question index that doesn't correspond to a test question."""
        mts = MarkingTaskService()
        paper1 = baker.make(Paper, paper_number=1)
        user0: User = baker.make(User)
        baker.make(
            MarkingTask,
            code="0001g2",
            status=MarkingTask.OUT_OF_DATE,
            assigned_user=user0,
            paper=paper1,
            question_index=2,
        )
        self.assertRaises(ValueError, mts.set_paper_marking_task_outdated, 1, 3)

    def test_marking_outdated4(self) -> None:
        """Test marking_outdated when there are multiple editions."""
        mts = MarkingTaskService()
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)

        task = baker.make(
            MarkingTask,
            code="0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper2,
            question_index=1,
        )
        MarkingTaskService.assign_task_to_user(task.pk, user0)
        img1 = baker.make(AnnotationImage)
        a1 = _create_new_annotation_in_database(
            task,
            1 / 3,
            17,
            img1,
            {
                "sceneItems": [
                    ["Rubric", 0, 0, {"rid": self.rubric1_on_3.rid, "revision": 0}],
                ]
            },
        )
        task.latest_annotation == a1
        img2 = baker.make(AnnotationImage)
        a2 = _create_new_annotation_in_database(
            task,
            3.0,
            21,
            img2,
            {
                "sceneItems": [
                    ["Rubric", 0, 0, {"rid": self.rubric3.rid, "revision": 0}]
                ]
            },
        )
        task.refresh_from_db()
        # creating the new annotation replaces the task's latest annotation
        task.latest_annotation != a1
        task.latest_annotation == a2

        assert a2.edition > a1.edition

        # now we make the task outdated
        mts.set_paper_marking_task_outdated(2, 1)
        task.refresh_from_db()
        assert task.status == MarkingTask.OUT_OF_DATE
        # Do we care?  Maybe is illdefined what latest should point to?
        task.latest_annotation == a2

    def test_marking_submits_non_existent_rubrics(self) -> None:
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)
        baker.make(QuestionPage, paper=paper2, page_number=3, question_index=1)
        task = baker.make(
            MarkingTask,
            code="0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper2,
            question_index=1,
        )
        MarkingTaskService.assign_task_to_user(task.pk, user0)
        img = baker.make(AnnotationImage)
        data = {"sceneItems": [["Rubric", 1, 1, {"rid": 123456, "revision": 42}]]}
        with self.assertRaises(KeyError):
            _create_new_annotation_in_database(task, 3.0, 21, img, data)

    def test_marking_submits_outofdate_rubric(self) -> None:
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)
        baker.make(QuestionPage, paper=paper2, page_number=3, question_index=1)
        task = baker.make(
            MarkingTask,
            code="0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper2,
            question_index=1,
        )
        rold = baker.make(Rubric, question_index=1, revision=9, latest=False)
        baker.make(Rubric, question_index=1, rid=rold.rid, revision=10, latest=True)
        MarkingTaskService.assign_task_to_user(task.pk, user0)
        img = baker.make(AnnotationImage)
        data = {
            "sceneItems": [
                ["Rubric", 1, 1, {"rid": rold.rid, "revision": rold.revision}]
            ]
        }
        with self.assertRaisesRegex(PlomConflict, "not the latest revision"):
            _create_new_annotation_in_database(
                task, 3.0, 21, img, data, require_latest_rubrics=True
            )

    def test_marking_submits_unpublished_rubric(self) -> None:
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)
        baker.make(QuestionPage, paper=paper2, page_number=3, question_index=1)
        task = baker.make(
            MarkingTask,
            code="0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper2,
            question_index=1,
        )
        r = baker.make(
            Rubric, question_index=1, revision=9, latest=True, published=False
        )
        MarkingTaskService.assign_task_to_user(task.pk, user0)
        img = baker.make(AnnotationImage)
        data = {
            "sceneItems": [["Rubric", 1, 1, {"rid": r.rid, "revision": r.revision}]]
        }
        with self.assertRaisesRegex(PlomConflict, "not currently published"):
            _create_new_annotation_in_database(
                task, 3.0, 21, img, data, require_latest_rubrics=True
            )

    def test_marking_rubric_from_wrong_question(self) -> None:
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)
        # make a question-page for this so that the 'is question ready' checker can verify that the question actually exists.
        # todo - this should likely be replaced with a spec check
        baker.make(QuestionPage, paper=paper2, page_number=3, question_index=1)

        task = baker.make(
            MarkingTask,
            code="0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper2,
            question_index=1,
        )
        MarkingTaskService.assign_task_to_user(task.pk, user0)
        img1 = baker.make(AnnotationImage)
        with self.assertRaisesRegex(PlomInconsistentRubric, "does not belong to"):
            _create_new_annotation_in_database(
                task,
                1,
                17,
                img1,
                {
                    "sceneItems": [
                        ["Rubric", 0, 0, {"rid": self.rubric_q2.rid, "revision": 0}],
                    ]
                },
            )

    def test_marking_rubric_wrong_scores(self) -> None:
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)
        # make a question-page for this so that the 'is question ready' checker can verify that the question actually exists.
        # todo - this should likely be replaced with a spec check
        baker.make(QuestionPage, paper=paper2, page_number=3, question_index=1)

        task = baker.make(
            MarkingTask,
            code="0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper2,
            question_index=1,
        )
        MarkingTaskService.assign_task_to_user(task.pk, user0)
        img1 = baker.make(AnnotationImage)
        with self.assertRaisesRegex(PlomConflict, "Conflict between"):
            _create_new_annotation_in_database(
                task,
                1 / 3,
                17,
                img1,
                {
                    "sceneItems": [
                        [
                            "Rubric",
                            0,
                            0,
                            {"rid": self.rubric1_on_3_poor_rounding.rid, "revision": 0},
                        ],
                    ]
                },
            )
        with self.assertRaisesRegex(PlomConflict, "Conflict between"):
            _create_new_annotation_in_database(
                task,
                1,
                17,
                img1,
                {
                    "sceneItems": [
                        ["Rubric", 0, 0, {"rid": self.rubric3.rid, "revision": 0}],
                    ]
                },
            )

    def test_marking_rubric_no_rubrics_used(self) -> None:
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)
        # make a question-page for this so that the 'is question ready' checker can verify that the question actually exists.
        # todo - this should likely be replaced with a spec check
        baker.make(QuestionPage, paper=paper2, page_number=3, question_index=1)

        task = baker.make(
            MarkingTask,
            code="0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper2,
            question_index=1,
        )
        MarkingTaskService.assign_task_to_user(task.pk, user0)
        img1 = baker.make(AnnotationImage)
        with self.assertRaisesRegex(PlomInconsistentRubric, "computed score is None"):
            _create_new_annotation_in_database(task, 0, 17, img1, {"sceneItems": []})
