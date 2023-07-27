# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import transaction, IntegrityError

from Identify.models import (
    PaperIDTask,
    PaperIDAction,
)
from Papers.models import IDPage, Paper


class IdentifyTaskService:
    """Class to encapsulate methods for handing out paper identification tasks to the client."""

    @transaction.atomic
    def are_there_id_tasks(self):
        """Return True if there is at least one ID task in the database."""
        # TO_DO - do we need to exclude "out of date" tasks here
        return PaperIDTask.objects.exists()

    @transaction.atomic
    def create_task(self, paper):
        """Create an identification task for a paper.

        Args:
            paper: a Paper instance
        """
        task = PaperIDTask(paper=paper)
        task.save()

    @transaction.atomic
    def id_task_exists(self, paper):
        """Return true if an ID tasks exists for a particular paper."""
        # TO_DO - do we need to exclude "out of date" tasks here
        return PaperIDTask.objects.filter(paper=paper).exists()

    @transaction.atomic
    def get_latest_id_results(self, task):
        """Return the latest (valid) results from a PaperIDAction instance.

        Args:
            task: reference to a PaperIDTask instance
        """
        latest = task.latest_action
        if latest:
            if latest.is_valid:
                return latest

        return None

    @transaction.atomic
    def get_done_tasks(self, user):
        """Retrieve the results of previously completed (and valid) ID tasks for a user.

        Args:
            user: reference to a User instance

        Returns:
            list: a list of 3-lists of the form
            ``[[paper_id, student_id, student_name], [...]]``.
        """
        id_list = []
        for task in PaperIDTask.objects.filter(
            status=PaperIDTask.COMPLETE, assigned_user=user
        ):
            latest = self.get_latest_id_results(task)
            if latest:
                id_list.append(
                    [task.paper.paper_number, latest.student_id, latest.student_name]
                )
        return id_list

    @transaction.atomic
    def get_id_progress(self):
        """Send back current ID progress counts to the client.

        Returns:
            list: A list including the number of identified papers
                and the total number of papers.
        """
        n_completed = PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE).count()
        n_total = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE).count()

        return [n_completed, n_total]

    @transaction.atomic
    def get_next_task(self):
        """Return the next available identification task, ordered by paper_number."""
        todo_tasks = PaperIDTask.objects.filter(status=PaperIDTask.TO_DO)
        todo_tasks = todo_tasks.order_by("paper__paper_number")
        if todo_tasks:
            return todo_tasks.first()

    @transaction.atomic
    def claim_task(self, user, paper_number):
        """Claim an ID task for a user."""
        try:
            task = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE).get(
                paper__paper_number=paper_number
            )
        except PaperIDTask.DoesNotExist:
            raise RuntimeError(f"Task with paper number {paper_number} does not exist.")

        if task.status == PaperIDTask.OUT:
            raise RuntimeError("Task is currently assigned.")
        elif task.status == PaperIDTask.COMPLETE:
            raise RuntimeError("Task has already been identified.")

        task.assigned_user = user
        task.status = PaperIDTask.OUT
        task.save()

    @transaction.atomic
    def get_id_page(self, paper_number):
        """Return the ID page image of a certain test-paper."""
        id_page = IDPage.objects.get(paper__paper_number=paper_number)
        id_img = id_page.image
        return id_img

    @transaction.atomic
    def identify_paper(self, user, paper_number, student_id, student_name):
        """Identify a test-paper and close its associated task.

        Raises:
            ObjectDoesNotExist: when there is no valid task associated to that paper
            PermissionDenied: when the user is not the assigned user for the id-ing task for that paper
            IntegrityError: the student id has already been assigned to a different paper
        """
        try:
            task = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE).get(
                paper__paper_number=paper_number
            )
        except PaperIDTask.DoesNotExist:
            raise ObjectDoesNotExist(
                f"Valid task for paper number {paper_number} does not exist."
            )

        if task.assigned_user != user:
            raise PermissionDenied(
                f"Task for paper number {paper_number} is not assigned to user {user}."
            )

        # look to see if that SID has been used in another valid PaperIDAction.
        # if one exists, then be careful to check if we are re-id'ing the current paper with same SID.
        try:
            prev_action_with_that_sid = PaperIDAction.objects.filter(
                is_valid=True, student_id=student_id
            ).get()
            if prev_action_with_that_sid != task.latest_action:
                raise IntegrityError(
                    "Student ID {student_id} has already been used in paper {prev_action_with_that_sid.PaperIDTask.paper.paper_number}"
                )
        except PaperIDAction.DoesNotExist:
            # The SID has not been used previously.
            pass

        # set the previous action (if it exists) to be invalid
        if task.latest_action:
            prev_action = task.latest_action
            prev_action.is_valid = False
            prev_action.save()

        # now make a new id-action
        new_action = PaperIDAction(
            user=user,
            task=task,
            student_id=student_id,
            student_name=student_name,
        )
        new_action.save()

        # update the task's latest-action pointer, and set its status to completed
        task.latest_action = new_action
        task.status = PaperIDTask.COMPLETE
        task.save()

    @transaction.atomic
    def surrender_task(self, user, task):
        """Remove a user from an id-ing task and set its status to 'todo'.

        Args:
            user: reference to a User instance
            task: reference to a MarkingTask instance
        """
        # only set status back to "TODO" if the task is OUT
        if task.status == PaperIDTask.OUT:
            task.assigned_user = None
            task.status = PaperIDTask.TO_DO
            task.save()

    @transaction.atomic
    def surrender_all_tasks(self, user):
        """Surrender all of the tasks currently assigned to the user.

        Args:
            user: reference to a User instance
        """
        user_tasks = PaperIDTask.objects.filter(
            assigned_user=user, status=PaperIDTask.OUT
        )
        for task in user_tasks:
            self.surrender_task(user, task)

    @transaction.atomic
    def set_paper_idtask_outdated(self, paper_number):
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError(f"Cannot find paper {paper_number}")

        try:
            task_obj = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE).get(
                paper=paper_obj
            )
        except PaperIDTask.DoesNotExist:
            raise ValueError(
                f"Cannot find valid PaperIDTask associated with paper {paper_number}"
            )
        except PaperIDTask.MultipleObjectsReturned:
            raise ValueError(
                f"Very serious error - have found multiple valid ID-tasks for paper {paper_number}"
            )

        if task_obj.status == PaperIDTask.OUT_OF_DATE:
            return
        # set the last id-action as invalid (if it exists)
        if task_obj.latest_action:
            latest_action = task_obj.latest_action
            latest_action.is_valid = False
            latest_action.save()
        # now set status and make assigned user None
        task_obj.assigned_user = None
        task_obj.status = PaperIDTask.OUT_OF_DATE
        task_obj.save()
