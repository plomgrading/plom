# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from Preparation.services import PQVMappingService
from Papers.services import SpecificationService
from Papers.models import Paper

from Mark.models import MarkingTask


class MarkingTaskService:
    """
    Functions for creating and modifying marking tasks.
    """

    def create_task(self, paper, question_number, user=None):
        """
        Create a marking task.

        Args:
            paper: a Paper instance, the test paper of the task
            question_number: int, the question of the task
            user: optional, User instance: user assigned to the task
        """

        pqvs = PQVMappingService()
        if not pqvs.is_there_a_pqv_map():
            raise RuntimeError("Server does not have a question-version map.")

        pqv_map = pqvs.get_pqv_map_dict()
        question_version = pqv_map[paper.paper_number][question_number]

        task_code = f"q{paper.paper_number:04}g{question_number}"

        the_task = MarkingTask(
            assigned_user=user,
            code=task_code,
            paper=paper,
            question_number=question_number,
            question_version=question_version,
        )
        the_task.save()
        return the_task

    def init_all_tasks(self):
        """
        Initialize all of the marking tasks for an entire exam, with null users.
        """

        spec_service = SpecificationService()
        if not spec_service.is_there_a_spec():
            raise RuntimeError("The server does not have a spec.")

        spec = spec_service.get_the_spec()
        n_questions = spec["numberOfQuestions"]

        all_papers = Paper.objects.all()
        for p in all_papers:
            for i in range(1, n_questions + 1):
                self.create_task(p, i)

    def get_task(self, paper_number, question_number):
        """
        Get a marking task from its paper number and question number.

        Args:
            paper_number: int
            question_number: int
        """
        paper = Paper.objects.get(paper_number=paper_number)
        return MarkingTask.objects.get(paper=paper, question_number=question_number)

    def get_task_from_code(self, code):
        """
        Get a marking task from its code.

        Arg:
            code: str, a unique string that includes the paper number and question number.
        """

        assert len(code) == len("q0000g0")
        paper_number = int(code[1:5])
        question_number = int(code[-1])

        return self.get_task(paper_number, question_number)

    def get_first_available_task(self):
        """
        Return the first marking task with a 'todo' status.
        """

        available = MarkingTask.objects.filter(status="todo")
        return available.first()

    def are_there_tasks(self):
        """
        Return True if there is at least one marking task in the database.
        """

        return MarkingTask.objects.exists()
