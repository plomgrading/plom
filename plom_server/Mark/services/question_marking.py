# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates

from typing import Optional, List
from dataclasses import asdict

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.models import User
from django.db import transaction

from ..models import MarkingTask
from . import mark_task, page_data, mark_tags


class QuestionMarkingService:
    """Handles the workflow of markers grading individual tasks.

    Takes care of handing out tasks and accepting marks:
        1. Marker makes a request for a new task to grade
        2. Server returns the best available task based on
            status and priority
        3. Marker makes a request to be assigned to that task
        4. Server double-checks if the task is available:
            - the status must be TO_DO
            - there must not be a user already assigned to the task
            and if so, assigns the user to the task.
        5. Marker annotates page-images and sends the annotations and
            mark to the server
        6. Server double-checks that the marker is still allowed to
            mark the task:
            - if the manager has assigned the task to someone else,
                the server rejects the annotations + mark
            - also, if the task's status has been changed to out-of-date,
                the server rejects the request
        7. Server saves mark, annotation data, and annotation image
        8. Return to step 5 - Marker is free to keep sending new marks for the task.
    """

    def __init__(
        self,
        *,
        task_pk: Optional[int] = None,
        code: Optional[str] = None,
        question: Optional[int] = None,
        version: Optional[int] = None,
        user: Optional[User] = None,
        marking_data: Optional[dict] = None,
        plomfile_data: Optional[str] = None,
        annotation_image: Optional[InMemoryUploadedFile] = None,
    ):
        """Service constructor.

        Args:
            task_pk: public key of a task instance
            code: string representing a paper number + question number pair
            question: question number of task
            version: question version of task
            user: reference to a user instance
            marking_data: dict representing a mark, rubrics used, etc
            plomfile_data: a stringified JSON blob representing an annotation SVG
            annotation_image: an in-memory raster representation of an annotation
        """
        self.task_pk = task_pk
        self.code = code
        self.question = question
        self.version = version
        self.user = user
        self.marking_data = marking_data
        self.plomfile_data = plomfile_data
        self.annotation_image = annotation_image

    @transaction.atomic
    def get_first_available_task(self) -> Optional[MarkingTask]:
        """Return the first marking task with a 'todo' status, sorted by `marking_priority`.

        If the priority is the same, defer to paper number and then question number.

        Returns:
            A reference to the first available task, or
            `None` if no such task exists.
        """
        available = MarkingTask.objects.filter(status=MarkingTask.TO_DO)

        if self.question:
            available = available.filter(question_number=self.question)

        if self.version:
            available = available.filter(question_version=self.version)

        if not available.exists():
            return None

        first_task = available.order_by(
            "-marking_priority", "paper__paper_number", "question_number"
        ).first()
        self.task_pk = first_task.pk
        return first_task

    @transaction.atomic
    def assign_task_to_user(self) -> MarkingTask:
        """Assign a specific marking task to a user.

        Fails if the relevant task can't be found, or the task cannot be
        assigned to that user.
        """
        if self.task_pk:
            task_to_assign = MarkingTask.objects.get(pk=self.task_pk)
        elif self.code:
            paper_number, question_number = mark_task.unpack_code(self.code)
            task_to_assign = mark_task.get_latest_task(paper_number, question_number)
            self.task_pk = task_to_assign.pk
        else:
            raise ValueError("Cannot find task to assign.")

        if task_to_assign.status != MarkingTask.TO_DO:
            raise ValueError("Task is currently assigned.")

        if not self.user or task_to_assign.assigned_user is not None:
            raise RuntimeError("Unable to assign task to user.")

        task_to_assign.assigned_user = self.user
        task_to_assign.status = MarkingTask.OUT
        task_to_assign.save()
        self.task_pk = task_to_assign.pk

        return task_to_assign

    @transaction.atomic
    def get_page_data(self) -> List[dict]:
        """Return the relevant data for rendering task pages on the client."""
        if self.task_pk:
            task = MarkingTask.objects.get(pk=self.task_pk)
            paper_number = task.paper.paper_number
            question_number = task.question_number
        elif self.code:
            paper_number, question_number = mark_task.unpack_code(self.code)
        else:
            raise ValueError("Cannot find task to read from.")

        pages = page_data.get_question_pages_list(paper_number, question_number)
        return [asdict(pd) for pd in pages]

    @transaction.atomic
    def get_tags(self) -> List[str]:
        """Return all the tags for a task."""
        if self.task_pk:
            task = MarkingTask.objects.get(pk=self.task_pk)
        elif self.code:
            paper_number, question_number = mark_task.unpack_code(self.code)
            task = mark_task.get_latest_task(paper_number, question_number)
            self.task_pk = task.pk
        else:
            raise ValueError("Cannot find task to read from.")

        return mark_tags.get_tag_texts_for_task(task)
