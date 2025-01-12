# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Aidan Murphy

from django.test import TestCase
from django.core.exceptions import MultipleObjectsReturned
from django.contrib.auth.models import User
from model_bakery import baker

from Papers.models import Paper, QuestionPage
from Rubrics.models import Rubric

from plom.plom_exceptions import PlomConflict
from ..services import MarkingTaskService
from ..models import MarkingTask, AnnotationImage
from ..services.annotations import _create_new_annotation_in_database


class MiscIncomingAnnotationsTests(TestCase):
    # some existing rests imported here and split into multiple parts
    def test_marking_outdated(self) -> None:
        mts = MarkingTaskService()
        self.assertRaises(ValueError, mts.set_paper_marking_task_outdated, 1, 1)
        baker.make(Paper, paper_number=1)
        self.assertRaises(ValueError, mts.set_paper_marking_task_outdated, 1, 1)

    def test_marking_outdated2(self) -> None:
        mts = MarkingTaskService()
        paper1 = baker.make(Paper, paper_number=1)

        user0: User = baker.make(User)
        baker.make(
            MarkingTask,
            code="q0001g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper1,
            question_index=1,
        )
        baker.make(
            MarkingTask,
            code="q0001g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper1,
            question_index=1,
        )
        self.assertRaises(
            MultipleObjectsReturned, mts.set_paper_marking_task_outdated, 1, 1
        )

    def test_marking_outdated3(self) -> None:
        mts = MarkingTaskService()
        paper1 = baker.make(Paper, paper_number=1)
        user0: User = baker.make(User)
        baker.make(
            MarkingTask,
            code="q0001g2",
            status=MarkingTask.OUT_OF_DATE,
            assigned_user=user0,
            paper=paper1,
            question_index=2,
        )
        self.assertRaises(ValueError, mts.set_paper_marking_task_outdated, 1, 2)

    def test_marking_outdated4(self) -> None:
        mts = MarkingTaskService()
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)
        # make a question-page for this so that the 'is question ready' checker can verify that the question actually exists.
        # todo - this should likely be replaced with a spec check
        baker.make(QuestionPage, paper=paper2, page_number=3, question_index=1)

        task = baker.make(
            MarkingTask,
            code="q0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper2,
            question_index=1,
        )
        MarkingTaskService.assign_task_to_user(task.pk, user0)
        img1 = baker.make(AnnotationImage)
        a1 = _create_new_annotation_in_database(
            task, 1 / 3, 17, img1, {"sceneItems": []}
        )
        task.latest_annotation == a1
        img2 = baker.make(AnnotationImage)
        a2 = _create_new_annotation_in_database(task, 3.0, 21, img2, {"sceneItems": []})
        task.latest_annotation != a1
        task.latest_annotation == a2

        assert a2.edition > a1.edition

        mts.set_paper_marking_task_outdated(2, 1)
        # Do we care?  Maybe is illdefined what latest should point to?
        task.latest_annotation == a2
        # TODO: test the effects of setting something out of date.

    def test_marking_submits_non_existent_rubrics(self) -> None:
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)
        baker.make(QuestionPage, paper=paper2, page_number=3, question_index=1)
        task = baker.make(
            MarkingTask,
            code="q0002g1",
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
            code="q0002g1",
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
                task, 3.0, 21, img, data, require_uptodate_rubrics=True
            )

    def test_marking_submits_unpublished_rubric(self) -> None:
        user0: User = baker.make(User)
        paper2 = baker.make(Paper, paper_number=2)
        baker.make(QuestionPage, paper=paper2, page_number=3, question_index=1)
        task = baker.make(
            MarkingTask,
            code="q0002g1",
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
                task, 3.0, 21, img, data, require_uptodate_rubrics=True
            )
