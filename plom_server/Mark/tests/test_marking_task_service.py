# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Andrew Rechnitzer

from django.test import TestCase
from django.contrib.auth.models import User
from model_bakery import baker

from Preparation.models import StagingPQVMapping
from Papers.models import Paper, QuestionPage, Image

from ..services import MarkingTaskService
from ..models import MarkingTask, AnnotationImage
from Papers.services import ImageBundleService


class MarkingTaskServiceTests(TestCase):
    """
    Unit tests for Mark.services.MarkingTaskService
    """

    def test_unpack_code(self):
        """
        Test MarkingTaskService.unpack_code
        """

        mts = MarkingTaskService()
        with self.assertRaises(AssertionError):
            mts.unpack_code("")

        with self.assertRaises(AssertionError):
            mts.unpack_code("astringthatdoesn'tstartwithq")

        with self.assertRaises(AssertionError):
            mts.unpack_code("qastrinGthatdoesn'tcontainalowercaseG")

        with self.assertRaises(ValueError):
            mts.unpack_code("q000qge")

        paper_number, question_number = mts.unpack_code("q0001g2")
        self.assertEqual(paper_number, 1)
        self.assertEqual(question_number, 2)

    def test_unpack_code_additional_tests(self):
        mts = MarkingTaskService()
        with self.assertRaises(AssertionError):
            mts.unpack_code("g0001q2")

        _, q1 = mts.unpack_code("q0001g2")
        _, q2 = mts.unpack_code("q0001g02")

        self.assertEqual(q1, q2)

        _, q1 = mts.unpack_code("q0001g2")
        _, q2 = mts.unpack_code("q0001g22")

        self.assertNotEqual(q1, q2)

        p1, q1 = mts.unpack_code("q1234567890987654321g8888888855555555123412341324")
        p2, q2 = mts.unpack_code("q1234567890987654321g9090909090909090909090909090")
        p3, q3 = mts.unpack_code("q9876543100123456789g9090909090909090909090909090")

        self.assertEqual(p1, p2)
        self.assertNotEqual(p1, p3)
        self.assertEqual(q2, q3)
        self.assertNotEqual(q1, q3)

        p1, q1 = mts.unpack_code("q8g9")
        self.assertEqual(p1, 8)
        self.assertEqual(q1, 9)

    def test_get_latest_task_no_paper_nor_question(self):
        s = MarkingTaskService()
        with self.assertRaisesRegexp(RuntimeError, "Task .*does not exist"):
            s.get_task_from_code("q0042g42")

    def test_get_latest_task_has_paper_but_no_question(self):
        s = MarkingTaskService()
        task = baker.make(
            MarkingTask, question_number=1, paper__paper_number=42, code="q0042g1"
        )
        code = "q0042g9"
        assert task.code != code
        with self.assertRaisesRegexp(RuntimeError, "Task .*does not exist"):
            s.get_task_from_code(code)

    def test_get_first_available_task(self):
        """
        Test MarkingTaskService.get_first_available_task()
        """

        baker.make(
            MarkingTask,
            status=MarkingTask.COMPLETE,
            paper__paper_number=1,
            code="1",
        )
        baker.make(MarkingTask, status=MarkingTask.OUT, paper__paper_number=2, code="2")
        task3 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            paper__paper_number=3,
            code="3",
            marking_priority=2,
        )
        baker.make(
            MarkingTask, status=MarkingTask.COMPLETE, paper__paper_number=4, code="4"
        )
        task5 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            paper__paper_number=5,
            code="5",
            marking_priority=1,
        )

        mts = MarkingTaskService()
        task = mts.get_first_available_task()
        self.assertEqual(task, task3)
        task3.status = MarkingTask.OUT
        task3.save()

        next_task = mts.get_first_available_task()
        self.assertEqual(next_task, task5)

    def test_get_first_filter(self):
        """
        Test MarkingTaskService.get_first_available_task() with a specified question and version
        """

        baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=1,
            question_version=1,
            paper__paper_number=1,
            code="1",
            marking_priority=1,
        )
        task2 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=1,
            question_version=2,
            paper__paper_number=2,
            code="2",
            marking_priority=2,
        )
        baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=2,
            question_version=2,
            paper__paper_number=3,
            code="3",
            marking_priority=3,
        )

        mts = MarkingTaskService()
        task = mts.get_first_available_task(1, 2)
        self.assertEqual(task, task2)

    def test_set_task_priorities(self):
        task1 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=1,
            question_version=1,
            paper__paper_number=1,
            code="1",
        )
        task2 = baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=1,
            question_version=2,
            paper__paper_number=2,
            code="2",
        )
        baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=2,
            question_version=2,
            paper__paper_number=3,
            code="3",
        )

        mts = MarkingTaskService()
        mts.set_task_priorities("papernum")

        task = mts.get_first_available_task()
        self.assertEqual(task, task1)
        task1.status = MarkingTask.COMPLETE
        task1.save()

        task = mts.get_first_available_task()
        self.assertEqual(task, task2)

    def test_set_task_priorities_more(self):
        baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=1,
            question_version=1,
            paper__paper_number=1,
            code="1",
        )
        baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=1,
            question_version=2,
            paper__paper_number=2,
            code="2",
        )
        baker.make(
            MarkingTask,
            status=MarkingTask.TO_DO,
            question_number=2,
            question_version=2,
            paper__paper_number=3,
            code="3",
        )

        mts = MarkingTaskService()
        mts.set_task_priorities(
            order_by="custom", custom_order={(1, 1): 8.9, (2, 1): 359.2, (3, 2): -16.3}
        )

        task = mts.get_first_available_task()
        self.assertEqual(task.code, "2")
        task.status = MarkingTask.COMPLETE
        task.save()

        self.assertAlmostEqual(MarkingTask.objects.get(code="1").marking_priority, 8.9)
        self.assertAlmostEqual(
            MarkingTask.objects.get(code="3").marking_priority, -16.3
        )

        task = mts.get_first_available_task()
        task.status = MarkingTask.COMPLETE
        task.save()

        task = mts.get_first_available_task()
        self.assertEqual(task.code, "3")

    def test_set_task_priorities_random(self):
        p = 1
        for q in range(2, 4):
            for v in range(1, 3):
                baker.make(
                    MarkingTask,
                    status=MarkingTask.TO_DO,
                    question_number=q,
                    question_version=v,
                    paper__paper_number=p,
                    code="1",
                    marking_priority=-1,
                )
                p += 1

        mts = MarkingTaskService()
        mts.set_task_priorities(order_by="random")

        for task in MarkingTask.objects.all():
            self.assertNotEqual(task.marking_priority, -1)

    def test_assign_task_to_user(self):
        """
        Test MarkingTaskService.assign_task_to_user()
        """

        user1 = baker.make(User)
        user2 = baker.make(User)
        task = baker.make(MarkingTask, status=MarkingTask.TO_DO)

        mts = MarkingTaskService()
        mts.assign_task_to_user(user1, task)
        task.refresh_from_db()
        self.assertEqual(task.status, MarkingTask.OUT)
        self.assertEqual(task.assigned_user, user1)

        with self.assertRaisesMessage(RuntimeError, "Task is currently assigned."):
            mts.assign_task_to_user(user2, task)

        task.refresh_from_db()
        self.assertEqual(task.assigned_user, user1)

    def test_surrender_task(self):
        """
        Test MarkingTaskService.surrender_task()
        """

        user = baker.make(User)
        task = baker.make(MarkingTask, status=MarkingTask.OUT)
        mts = MarkingTaskService()

        mts.surrender_task(user, task)
        task.refresh_from_db()
        self.assertEqual(task.status, MarkingTask.TO_DO)

    def test_user_can_update_task(self):
        """
        Test MarkingTaskService.user_can_update_task()
        """

        user = baker.make(User)
        other_user = baker.make(User)
        paper1 = baker.make(Paper, paper_number=1)
        paper2 = baker.make(Paper, paper_number=2)
        paper3 = baker.make(Paper, paper_number=3)
        paper4 = baker.make(Paper, paper_number=4)
        paper5 = baker.make(Paper, paper_number=5)

        baker.make(
            MarkingTask,
            code="q0001g1",
            status=MarkingTask.OUT,
            assigned_user=user,
            paper=paper1,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=None,
            paper=paper2,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0003g1",
            status=MarkingTask.OUT,
            assigned_user=other_user,
            paper=paper3,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0004g1",
            status=MarkingTask.COMPLETE,
            assigned_user=user,
            paper=paper4,
            question_number=1,
        )
        baker.make(
            MarkingTask,
            code="q0005g1",
            status=MarkingTask.COMPLETE,
            assigned_user=other_user,
            paper=paper5,
            question_number=1,
        )

        mts = MarkingTaskService()
        self.assertTrue(mts.user_can_update_task(user, "q0001g1"))
        self.assertFalse(mts.user_can_update_task(user, "q0002g1"))
        self.assertFalse(mts.user_can_update_task(user, "q0003g1"))
        self.assertTrue(mts.user_can_update_task(user, "q0004g1"))
        self.assertFalse(mts.user_can_update_task(user, "q0005g1"))

    def test_marking_outdated(self):
        mts = MarkingTaskService()
        self.assertRaises(ValueError, mts.set_paper_marking_task_outdated, 1, 1)
        paper1 = baker.make(Paper, paper_number=1)
        self.assertRaises(ValueError, mts.set_paper_marking_task_outdated, 1, 1)

        user0 = baker.make(User)
        task1a = baker.make(
            MarkingTask,
            code="q0001g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper1,
            question_number=1,
        )
        task1b = baker.make(
            MarkingTask,
            code="q0001g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper1,
            question_number=1,
        )
        self.assertRaises(ValueError, mts.set_paper_marking_task_outdated, 1, 1)

        task1c = baker.make(
            MarkingTask,
            code="q0001g2",
            status=MarkingTask.OUT_OF_DATE,
            assigned_user=user0,
            paper=paper1,
            question_number=2,
        )
        self.assertRaises(ValueError, mts.set_paper_marking_task_outdated, 1, 2)

        paper2 = baker.make(Paper, paper_number=2)
        # make a question-page for this so that the 'is question ready' checker can verify that the question actually exists.
        # todo - this should likely be replaced with a spec check
        qp2 = baker.make(QuestionPage, paper=paper2, page_number=3, question_number=1)

        task2a = baker.make(
            MarkingTask,
            code="q0002g1",
            status=MarkingTask.TO_DO,
            assigned_user=user0,
            paper=paper2,
            question_number=1,
        )
        mts.assign_task_to_user(user0, task2a)
        an_img1 = baker.make(AnnotationImage)
        mts.mark_task(user0, "q0002g1", 3, 17, an_img1, {"sceneItems": []})
        an_img2 = baker.make(AnnotationImage)
        mts.mark_task(user0, "q0002g1", 2, 21, an_img2, {"sceneItems": []})
        mts.set_paper_marking_task_outdated(2, 1)


class TestMarkingTasksWithFixtures(TestCase):
    fixtures = ["test_spec.json", "preparation.json", "papers.json"]

    def test_create_task(self):
        """Test MarkingTaskService.create_task()"""
        paper1 = Paper.objects.get(paper_number=1)
        paper2 = Paper.objects.get(paper_number=2)

        mts = MarkingTaskService()
        task1 = mts.create_task(paper1, 1)
        task2 = mts.create_task(paper2, 1)

        question_version1 = StagingPQVMapping.objects.get(
            paper_number=1, question=1
        ).version
        question_version2 = StagingPQVMapping.objects.get(
            paper_number=2, question=1
        ).version

        self.assertEqual(task1.question_version, question_version1)
        self.assertAlmostEqual(task1.code, "q0001g1")
        self.assertEqual(task2.question_version, question_version2)
        self.assertEqual(task2.code, "q0002g1")

    def test_marking_task_before_pqvmap(self):
        """Test that .create_task() fails if there is no QV map."""
        paper1 = Paper.objects.get(paper_number=1)

        # Remove QV map for testing purposes
        StagingPQVMapping.objects.all().delete()

        with self.assertRaises(RuntimeError):
            mts = MarkingTaskService()
            mts.create_task(paper1, 1)
