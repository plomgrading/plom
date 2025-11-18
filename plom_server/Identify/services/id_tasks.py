# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2025 Andrew Rechnitzer

from django.contrib.auth.models import User
from django.core.exceptions import (
    PermissionDenied,
    ObjectDoesNotExist,
    MultipleObjectsReturned,
)
from django.db import transaction, IntegrityError

from plom_server.Papers.models import IDPage, Paper, Image
from plom_server.Papers.services import ImageBundleService
from ..models import PaperIDTask, PaperIDAction, IDPrediction


class IdentifyTaskService:
    """Class to encapsulate methods for handing out paper identification tasks to the client."""

    @transaction.atomic
    def are_there_id_tasks(self) -> bool:
        """Return True if there is at least one ID task in the database.

        Note that this *does* exclude out-of-date tasks.
        """
        return PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE).exists()

    @transaction.atomic
    def create_task(self, paper: Paper) -> None:
        """Create an identification task for a paper. Set any older id-tasks for same paper as out of date.

        Args:
            paper: a Paper instance
        """
        for old_task in PaperIDTask.objects.filter(paper=paper):
            old_task.status = PaperIDTask.OUT_OF_DATE
            old_task.assigned_user = None
            old_task.save()
            # make sure that **all** outdated actions are marked as invalid.
            # don't assume that we only have to set the latest action
            for prev_action in old_task.paperidaction_set.all():
                prev_action.is_valid = False
                prev_action.save()

        task = PaperIDTask(paper=paper)
        task.save()

    @staticmethod
    def bulk_create_id_tasks(papers: list[Paper]) -> None:
        """For each given paper set any ID tasks and actions as out of date and create new tasks.

        For each paper in the list we set any existing ID tasks and actions as
        out of date and then create new ID tasks.

        These operations are all done in bulk to minimise DB access. So
        instead of looping over each paper and doing a ``save()'' we
        loop over the list and construct lists of PaperIDTask and PaperIDAction
        that need to be updated. We alter the corresponding python objects
        and then pass the list of those (locally) updated objects to a
        django bulk-update functions that minimise the number of DB calls.
        Similarly when we create new PaperIDTask in the DB we do not do
        this one at a time, but create a list of (local) python objects and
        then pass that list to django-bulk-create function that creates
        things minimising DB access.

        Args:
            papers: a list of Django-objects that require their ID tasks + actions
            updated. For example, if ID pages have been replaced then any existing
            ID tasks + actions need to be set as out-of-date and new ID tasks
            need to be instantiated.

        """
        with transaction.atomic():
            old_tasks = PaperIDTask.objects.filter(paper__in=papers)
            old_actions = PaperIDAction.objects.filter(task__in=old_tasks)
            for task in old_tasks:
                task.status = PaperIDTask.OUT_OF_DATE
                task.assigned_user = None
            PaperIDTask.objects.bulk_update(old_tasks, ["status", "assigned_user"])
            for action in old_actions:
                action.is_valid = False
            PaperIDAction.objects.bulk_update(old_actions, ["is_valid"])
            new_tasks = [PaperIDTask(paper=X) for X in papers]
            PaperIDTask.objects.bulk_create(new_tasks)

    @transaction.atomic
    def id_task_exists(self, paper: Paper) -> bool:
        """Return true if an ID tasks not OUT_OF_DATE exists for a particular paper."""
        return (
            PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE)
            .filter(paper=paper)
            .exists()
        )

    @transaction.atomic
    def get_latest_id_results(self, task: PaperIDTask) -> PaperIDAction | None:
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
    def get_done_tasks(self, user: User) -> list:
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
        ).prefetch_related("paper", "latest_action"):
            if task.latest_action:
                id_list.append(
                    [
                        task.paper.paper_number,
                        task.latest_action.student_id,
                        task.latest_action.student_name,
                    ]
                )
        return id_list

    @transaction.atomic
    def get_id_progress(self) -> list:
        """Send back current ID progress counts to the client.

        Returns:
            list: A list including the number of identified papers
                and the total number of papers.
        """
        n_completed = PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE).count()
        n_total = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE).count()

        return [n_completed, n_total]

    @transaction.atomic
    def get_next_task(self) -> PaperIDTask | None:
        """Return the next available identification task.

        Ordered by iding_priority then by paper number.
        """
        todo_tasks = PaperIDTask.objects.filter(status=PaperIDTask.TO_DO)
        todo_tasks = todo_tasks.order_by("-iding_priority", "paper__paper_number")
        if todo_tasks:
            return todo_tasks.first()
        else:
            return None

    @transaction.atomic
    def claim_task(self, user: User, paper_number: int) -> None:
        """Claim an ID task for a user."""
        try:
            task = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE).get(
                paper__paper_number=paper_number
            )
        except PaperIDTask.DoesNotExist:
            raise RuntimeError(
                f"ID Task with paper number {paper_number} does not exist."
            )

        if task.status == PaperIDTask.OUT:
            raise RuntimeError(f"ID task {paper_number} is currently assigned.")
        elif task.status == PaperIDTask.COMPLETE:
            raise RuntimeError(
                f"ID task {paper_number} is complete, already identified."
            )

        task.assigned_user = user
        task.status = PaperIDTask.OUT
        task.save()

    @transaction.atomic
    def get_id_page(self, paper_number: int) -> Image:
        """Return the ID page image of a certain test-paper."""
        id_page = IDPage.objects.get(paper__paper_number=paper_number)
        id_img = id_page.image
        return id_img

    @transaction.atomic
    def identify_paper(
        self, user: User, paper_number: int, student_id: str, student_name: str
    ) -> None:
        """Identify a test-paper and close its associated task.

        Raises:
            ObjectDoesNotExist: when there is no valid task associated to that paper
            PermissionDenied: when the user is not the assigned user for the id-ing task for that paper
            IntegrityError: the student id has already been assigned to a different paper
        """
        try:
            task = PaperIDTask.objects.exclude(
                status__in=[PaperIDTask.OUT_OF_DATE, PaperIDTask.TO_DO]
            ).get(paper__paper_number=paper_number)
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
        # re #2827 - we **skip** this check when the ID is blank
        if student_id:
            try:
                prev_action_with_that_sid = PaperIDAction.objects.filter(
                    is_valid=True, student_id=student_id
                ).get()
                if prev_action_with_that_sid != task.latest_action:
                    raise IntegrityError(
                        f"Student ID {student_id} has already been used in paper "
                        f"{prev_action_with_that_sid.paperidtask.paper.paper_number}"
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

    @staticmethod
    def surrender_all_tasks(user: User) -> None:
        """Surrender all of the tasks currently assigned to the user.

        Args:
            user: reference to a User instance
        """
        PaperIDTask.objects.filter(assigned_user=user, status=PaperIDTask.OUT).update(
            assigned_user=None, status=PaperIDTask.TO_DO
        )

    @transaction.atomic
    def set_paper_idtask_outdated(self, paper_number: int) -> None:
        try:
            paper_obj = Paper.objects.get(paper_number=paper_number)
        except Paper.DoesNotExist:
            raise ValueError(f"Cannot find paper {paper_number}")

        valid_tasks = PaperIDTask.objects.exclude(
            status=PaperIDTask.OUT_OF_DATE
        ).filter(paper=paper_obj)
        valid_task_count = valid_tasks.count()

        if valid_task_count > 1:
            raise MultipleObjectsReturned(
                f"Very serious error - have found multiple valid ID-tasks for paper {paper_number}"
            )
        if valid_task_count == 1:
            task_obj = valid_tasks.get()
            # set the last id-action as invalid (if it exists)
            if task_obj.latest_action:
                latest_action = task_obj.latest_action
                latest_action.is_valid = False
                latest_action.save()
            # now set status and make assigned user None
            task_obj.assigned_user = None
            task_obj.status = PaperIDTask.OUT_OF_DATE
            task_obj.save()

        # now all existing tasks are out of date, so if the id-page is ready then create a new id-task for it.
        if ImageBundleService().is_given_paper_ready_for_id_ing(paper_obj):
            self.create_task(paper_obj)

    @staticmethod
    @transaction.atomic
    def update_task_priority(paper_obj: Paper, *, increasing_cert: bool = True) -> None:
        """Update the iding_priority field for PaperIDTasks.

        Args:
            paper_obj: the paper whose priority to update.

        Keyword Args:
            increasing_cert: determines whether the sorting order for
                the priorities based on certainties is in increasing
                order. If false, it is in decreasing order.

        Raises:
            ValueError: The prediction or task does not exist for the given paper.
        """
        try:
            pred_query = IDPrediction.objects.filter(paper=paper_obj)
            cert_list = [pred.certainty for pred in pred_query]
            # always choose the minimum certainty if more than one prediction is available
            priority = min(cert_list)
        except IDPrediction.DoesNotExist as e:
            raise ValueError(
                f"No predictions exist for paper number {paper_obj.paper_number}."
            ) from e

        try:
            task = PaperIDTask.objects.exclude(status=PaperIDTask.OUT_OF_DATE).get(
                paper=paper_obj
            )
            if increasing_cert:
                task.iding_priority = -priority
            else:
                task.iding_priority = priority
            task.save()
        except PaperIDTask.DoesNotExist as e:
            raise ValueError(
                f"Task with paper number {paper_obj.paper_number} does not exist."
            ) from e

    @transaction.atomic
    def reset_task_priority(self) -> None:
        """Reset the priority of all TODO tasks to zero."""
        tasks = PaperIDTask.objects.filter(status=PaperIDTask.TO_DO)
        for task in tasks:
            task.iding_priority = 0
        PaperIDTask.objects.bulk_update(tasks, ["iding_priority"])
