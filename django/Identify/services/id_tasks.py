# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates

from Identify.models import (
    PaperIDTask,
    PaperIDAction,
)
from Papers.models import Paper, IDPage


class IdentifyTaskService:
    """
    Class to encapsulate methods for handing out paper identification tasks
    to the client.
    """

    def are_there_id_tasks(self):
        """
        Return True if there is at least one ID task in the database.
        """

        return PaperIDTask.objects.exists()

    def create_task(self, paper):
        """
        Create an identification task for a paper.

        Args:
            paper: a Paper instance
        """

        task = PaperIDTask(paper=paper)
        task.save()

    def id_task_exists(self, paper):
        """
        Return true if an ID tasks exists for a particular paper.
        """

        return PaperIDTask.objects.filter(paper=paper).exists()

    def get_latest_id_results(self, task):
        """
        Return the latest results from a PaperIDAction instance

        Args:
            task: reference to a PaperIDTask instance
        """

        latest = PaperIDAction.objects.filter(task=task)
        latest = latest.order_by("-time")
        if latest:
            return latest[0]

    def get_done_tasks(self, user):
        """
        Return the results of previously completed tasks for a user
        With the form [[paper_id, student_id, student_name]]
        """

        id_list = []
        done_tasks = PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE)
        for task in done_tasks:
            latest = self.get_latest_id_results(task)
            if latest and latest.user == user:
                id_list.append(
                    [task.paper.paper_number, latest.student_id, latest.student_name]
                )

        return id_list

    def get_id_progress(self):
        """Send back current ID progress counts to the client.

        Returns:
            list: A list including the number of identified papers
            and the total number of papers.
        """

        completed = PaperIDTask.objects.filter(status=PaperIDTask.COMPLETE)
        total = PaperIDTask.objects.all()

        return [len(completed), len(total)]

    def get_next_task(self):
        """
        Return the next available identification task.
        """

        todo_tasks = PaperIDTask.objects.filter(status=PaperIDTask.TO_DO)
        todo_tasks = todo_tasks.order_by("paper__paper_number")
        if todo_tasks:
            return todo_tasks.first()

    def claim_task(self, user, paper_number):
        """
        Claim an ID task for a user.
        """

        try:
            task = PaperIDTask.objects.get(paper__paper_number=paper_number)
        except PaperIDTask.DoesNotExist:
            raise RuntimeError(f"Task with paper number {paper_number} does not exist.")

        if task.status == PaperIDTask.OUT:
            raise RuntimeError("Task is currently assigned.")

        task.assigned_user = user
        task.status = PaperIDTask.OUT
        task.save()

    def get_id_page(self, paper_number):
        """
        Return the ID page image of a certain test-paper.
        """

        id_page = IDPage.objects.get(paper__paper_number=paper_number)
        id_img = id_page.image
        return id_img

    def identify_paper(self, user, paper_number, student_id, student_name):
        """
        Identify a test-paper and close its associated task.
        """

        try:
            task = PaperIDTask.objects.get(paper__paper_number=paper_number)
        except PaperIDTask.DoesNotExist:
            raise RuntimeError(f"Task with paper number {paper_number} does not exist.")

        id_action = PaperIDAction(
            user=user, task=task, student_id=student_id, student_name=student_name
        )
        id_action.save()

        task.status = PaperIDTask.COMPLETE
        task.save()

    def surrender_task(self, user, task):
        """
        Remove a user from a marking task, set its status to 'todo', and
        save the action to the database.

        Args:
            user: reference to a User instance
            task: reference to a MarkingTask instance
        """

        task.assigned_user = None
        task.status = PaperIDTask.TO_DO
        task.save()

    def surrender_all_tasks(self, user):
        """
        Surrender all of the tasks currently assigned to the user.

        Args:
            user: reference to a User instance
        """

        user_tasks = PaperIDTask.objects.filter(assigned_user=user, status=PaperIDTask.OUT)
        for task in user_tasks:
            self.surrender_task(user, task)
