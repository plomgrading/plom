# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from datetime import timedelta

from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
    MultipleObjectsReturned,
)
from django.db import IntegrityError
from model_bakery import baker

from plom_server.Papers.models import Paper, Image, IDPage
from .services import IdentifyTaskService, IDProgressService, IDDirectService
from .models import PaperIDTask, PaperIDAction


class IdentifyTaskTests(TestCase):
    """Tests for ``Identify.services.IdentifyTaskService`` and ``Identify.services.IDProgressService`` functions."""

    def setUp(self) -> None:
        self.marker0: User = baker.make(User, username="marker0")
        self.marker1: User = baker.make(User, username="marker1")
        return super().setUp()

    def test_are_there_id_tasks(self) -> None:
        """Test ``IdentifyTaskService.are_there_id_tasks()``."""
        its = IdentifyTaskService()
        self.assertFalse(its.are_there_id_tasks())

        baker.make(PaperIDTask)
        self.assertTrue(its.are_there_id_tasks())

    def test_get_done_tasks(self) -> None:
        """Test ``IdentifyTaskService.get_done_tasks()``."""
        its = IdentifyTaskService()
        self.assertEqual(its.get_done_tasks(user=self.marker0), [])

        paper = baker.make(Paper, paper_number=1)
        task = baker.make(
            PaperIDTask,
            paper=paper,
            status=PaperIDTask.COMPLETE,
            assigned_user=self.marker0,
        )
        id_act = baker.make(
            PaperIDAction,
            user=self.marker0,
            task=task,
            student_name="A",
            student_id="1",
            is_valid=True,
        )
        task.latest_action = id_act
        task.save()

        result = its.get_done_tasks(user=self.marker0)
        self.assertEqual(result, [[1, "1", "A"]])

    def test_get_latest_id_task(self) -> None:
        """Test ``IdentifyTaskService.get_latest_id_results()``."""
        its = IdentifyTaskService()
        paper = baker.make(Paper, paper_number=1)
        task1 = baker.make(PaperIDTask, paper=paper, assigned_user=self.marker0)
        self.assertIsNone(its.get_latest_id_results(task=task1))

        start_time = timezone.now()
        first = baker.make(
            PaperIDAction,
            time=start_time,
            task=task1,
            user=self.marker0,
            is_valid=True,
        )
        task1.latest_action = first
        task1.save()

        self.assertEqual(its.get_latest_id_results(task1), first)

        first.is_valid = False
        first.save()
        second = baker.make(
            PaperIDAction, time=start_time + timedelta(seconds=1), task=task1
        )
        task1.latest_action = second
        task1.save()

        self.assertEqual(its.get_latest_id_results(task1), second)

    def test_get_id_progress(self) -> None:
        """Test ``IdentifyTaskService.get_id_progress()``."""
        its = IdentifyTaskService()
        self.assertEqual(its.get_id_progress(), [0, 0])

        baker.make(PaperIDTask, status=PaperIDTask.COMPLETE)
        baker.make(PaperIDTask, status=PaperIDTask.TO_DO)
        baker.make(PaperIDTask, status=PaperIDTask.OUT)
        self.assertEqual(its.get_id_progress(), [1, 3])

    def test_get_next_task(self) -> None:
        """Test ``IdentifyTaskService.get_next_task()``."""
        its = IdentifyTaskService()
        self.assertIsNone(its.get_next_task())

        p1 = baker.make(Paper, paper_number=1)
        p2 = baker.make(Paper, paper_number=2)
        p3 = baker.make(Paper, paper_number=3)
        p4 = baker.make(Paper, paper_number=4)

        baker.make(PaperIDTask, status=PaperIDTask.OUT, paper=p1)
        t2 = baker.make(PaperIDTask, status=PaperIDTask.TO_DO, paper=p2)
        baker.make(PaperIDTask, status=PaperIDTask.OUT, paper=p3)
        baker.make(PaperIDTask, status=PaperIDTask.TO_DO, paper=p4)

        claimed = its.get_next_task()
        self.assertEqual(claimed, t2)

    def test_claim_task(self) -> None:
        """Test a simple case of ``IdentifyTaskService.claim_task()``."""
        its = IdentifyTaskService()
        with self.assertRaises(RuntimeError):
            its.claim_task(self.marker0, 1)

        p1 = baker.make(Paper, paper_number=1)
        task = baker.make(PaperIDTask, paper=p1)

        its.claim_task(self.marker0, 1)
        task.refresh_from_db()

        self.assertEqual(task.status, PaperIDTask.OUT)
        self.assertEqual(task.assigned_user, self.marker0)

    def test_out_claim_task(self) -> None:
        """Test that claiming a task throws an error if the task is currently out."""
        its = IdentifyTaskService()
        p1 = baker.make(Paper, paper_number=1)
        baker.make(PaperIDTask, paper=p1, status=PaperIDTask.OUT)

        with self.assertRaises(RuntimeError):
            its.claim_task(self.marker0, 1)

    def test_identify_paper(self) -> None:
        """Test a simple case for ``IdentifyTaskService.identify_paper()``."""
        its = IdentifyTaskService()
        with self.assertRaises(ObjectDoesNotExist):
            its.identify_paper(self.marker1, 1, "1", "A")

        p1 = baker.make(Paper, paper_number=1)

        task = baker.make(
            PaperIDTask, paper=p1, status=PaperIDTask.OUT, assigned_user=self.marker0
        )

        its.identify_paper(self.marker0, 1, "1", "A")
        task.refresh_from_db()

        self.assertEqual(task.status, PaperIDTask.COMPLETE)
        self.assertEqual(
            task.assigned_user, self.marker0
        )  # Assumption: user keeps task after ID'ing

        action = PaperIDAction.objects.get(user=self.marker0, task=task)
        self.assertEqual(action.student_name, "A")
        self.assertEqual(action.student_id, "1")

    def test_clear_id_from_paper(self) -> None:
        """Test ``IDProgressService().clear_id_from_paper()``."""
        ids = IDProgressService()
        paper = baker.make(Paper, paper_number=1)
        baker.make(PaperIDTask, paper=paper, status=PaperIDTask.COMPLETE)
        ids.clear_id_from_paper(1)

        with self.assertRaises(ValueError):
            ids.clear_id_from_paper(2)

        new_task = PaperIDTask.objects.get(paper=paper, status=PaperIDTask.TO_DO)
        self.assertQuerySetEqual(PaperIDAction.objects.filter(task=new_task), [])

    def test_clear_id_from_all_identified_papers(self) -> None:
        """Test ``IDProgressService().set_all_id_task_todo_and_clear_all_id_cmd()``."""
        ids = IDProgressService()
        for paper_number in range(1, 11):
            paper = baker.make(Paper, paper_number=paper_number)
            task = baker.make(PaperIDTask, paper=paper, status=PaperIDTask.COMPLETE)
            baker.make(PaperIDAction, task=task)

        ids.clear_id_from_all_identified_papers()

        for id_task in PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE):
            self.assertEqual(id_task.status, PaperIDTask.TO_DO)

    def test_id_already_used(self) -> None:
        """Test that using same ID twice raises exception."""
        its = IdentifyTaskService()
        for k in range(1, 3):
            paper = baker.make(Paper, paper_number=k)
            its.create_task(paper)
            its.claim_task(self.marker0, k)

        its.identify_paper(self.marker0, 1, "1", "ABC")
        self.assertRaises(
            IntegrityError, its.identify_paper, self.marker0, 2, "1", "ABC"
        )

    def test_claim_and_surrender(self) -> None:
        its = IdentifyTaskService()
        for k in range(1, 5):
            paper = baker.make(Paper, paper_number=k)
            its.create_task(paper)
        for k in range(1, 3):
            its.claim_task(self.marker0, k)
        its.surrender_all_tasks(self.marker0)

    def test_id_task_misc(self) -> None:
        """Test the number of id'd papers."""
        its = IdentifyTaskService()
        for k in range(1, 5):
            paper = baker.make(Paper, paper_number=k)
            its.create_task(paper)

        for k in range(1, 3):
            its.claim_task(self.marker0, k)
            its.identify_paper(self.marker0, k, f"{k}", f"A{k}")

        # test reclaiming a completed task
        self.assertRaises(RuntimeError, its.claim_task, self.marker1, 1)

        # test user ID'ing a task that does not belong to them
        self.assertRaises(
            PermissionDenied, its.identify_paper, self.marker1, 1, "1", "A1"
        )

        # test re-id'ing a task
        for k in range(1, 3):
            its.identify_paper(self.marker0, k, f"{k + 2}", f"A{k + 2}")

        # test task existence
        paper = baker.make(Paper, paper_number=10)
        self.assertFalse(its.id_task_exists(paper))
        its.create_task(paper)
        self.assertTrue(its.id_task_exists(paper))
        # make sure when it is out of date that this function shows false.
        its.set_paper_idtask_outdated(10)
        self.assertFalse(its.id_task_exists(paper))

    def test_idtask_outdated(self) -> None:
        its = IdentifyTaskService()
        self.assertRaises(ValueError, its.set_paper_idtask_outdated, 7)

        paper1 = baker.make(Paper, paper_number=1)
        baker.make(PaperIDTask, paper=paper1, status=PaperIDTask.OUT_OF_DATE)

        paper2 = baker.make(Paper, paper_number=2)
        baker.make(PaperIDTask, paper=paper2, status=PaperIDTask.TO_DO)
        baker.make(PaperIDTask, paper=paper2, status=PaperIDTask.TO_DO)
        self.assertRaises(MultipleObjectsReturned, its.set_paper_idtask_outdated, 2)

        paper3 = baker.make(Paper, paper_number=3)
        baker.make(PaperIDTask, paper=paper3, status=PaperIDTask.OUT_OF_DATE)
        baker.make(PaperIDTask, paper=paper3, status=PaperIDTask.TO_DO)
        its.claim_task(self.marker0, 3)
        its.identify_paper(self.marker0, 3, "3", "ABC")
        its.identify_paper(self.marker0, 3, "4", "CBA")
        its.set_paper_idtask_outdated(3)

    def test_idtask_recreate(self) -> None:
        its = IdentifyTaskService()
        # create a paper with at least one out-of-date tasks
        paper1 = baker.make(Paper, paper_number=1)
        baker.make(PaperIDTask, paper=paper1, status=PaperIDTask.OUT_OF_DATE)
        img1 = baker.make(Image)
        idp1 = baker.make(IDPage, paper=paper1, image=img1)
        # make a new task for it, claim it, and id it.
        its.create_task(paper1)
        its.claim_task(self.marker0, 1)
        its.identify_paper(self.marker0, 1, "3", "ABC")
        # now give the idpage a new image and set task as out of date (will create a new task)
        img2 = baker.make(Image)
        idp1.image = img2
        idp1.save()
        its.set_paper_idtask_outdated(1)
        its.claim_task(self.marker0, 1)
        its.identify_paper(self.marker0, 1, "4", "ABCD")

    def test_get_all_id_task_count(self) -> None:
        ids = IDProgressService()
        for n in range(1, 4):
            paper = baker.make(Paper, paper_number=n)
            baker.make(PaperIDTask, paper=paper, status=PaperIDTask.TO_DO)
        for n in range(4, 8):
            paper = baker.make(Paper, paper_number=n)
            baker.make(PaperIDTask, paper=paper, status=PaperIDTask.COMPLETE)
        self.assertEqual(7, ids.get_all_id_task_count())
        self.assertEqual(4, ids.get_completed_id_task_count())

    def test_get_all_id_task_info(self) -> None:
        its = IdentifyTaskService()
        ids = IDProgressService()

        for n in range(1, 3):
            paper = baker.make(Paper, paper_number=n)
            its.create_task(paper)

        for n in range(1, 2):
            its.claim_task(self.marker0, n)
            its.identify_paper(self.marker0, n, f"99{n}", f"AB{n}")

        info_dict = {
            1: {
                "idpageimage_pk": None,
                "status": "Complete",
                "student_id": "991",
                "student_name": "AB1",
                "in_classlist": False,
                "username": "marker0",
            },
            2: {"idpageimage_pk": None, "status": "To Do", "prediction": None},
        }

        self.assertEqual(info_dict, ids.get_all_id_task_info())

    def test_id_hw(self) -> None:
        its = IdentifyTaskService()
        ids = IDProgressService()

        for n in range(1, 3):
            paper = baker.make(Paper, paper_number=n)
            its.create_task(paper)
        for n in range(1, 3):
            IDDirectService.identify_direct(self.marker0, n, f"99{n}", f"AB{n}")
        info_dict = {
            1: {
                "idpageimage_pk": None,
                "status": "Complete",
                "student_id": "991",
                "student_name": "AB1",
                "in_classlist": False,
                "username": "marker0",
            },
            2: {
                "idpageimage_pk": None,
                "status": "Complete",
                "student_id": "992",
                "student_name": "AB2",
                "in_classlist": False,
                "username": "marker0",
            },
        }

        self.assertEqual(info_dict, ids.get_all_id_task_info())
