# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Colin B. Macdonald

from typing import Optional, List

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.models import User
from django.db import transaction

from ..models import MarkingTask
from . import mark_task, page_data, mark_tags, annotations


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
        min_paper_num: Optional[int] = None,
        max_paper_num: Optional[int] = None,
        tag: Optional[str] = None,
        marking_data: Optional[dict] = None,
        annotation_data: Optional[dict] = None,
        annotation_image: Optional[InMemoryUploadedFile] = None,
        annotation_image_md5sum: Optional[str] = None,
    ):
        """Service constructor.

        Args:
            task_pk: public key of a task instance
            code: string representing a paper number + question number pair
            question: question number of task
            version: question version of task
            user: reference to a user instance
            min_paper_num: the minimum paper number of the task
            max_paper_num: the maximum paper number of the task
            marking_data: dict representing a mark, rubrics used, etc
            annotation_data: a dictionary representing an annotation SVG
            annotation_image: an in-memory raster representation of an annotation
            annotation_image_md5sum: the hash for annotation_image
        """
        self.task_pk = task_pk
        self.code = code
        self.question = question
        self.version = version
        self.user = user
        self.min_paper_num = min_paper_num
        self.max_paper_num = max_paper_num
        self.marking_data = marking_data
        self.annotation_data = annotation_data
        self.annotation_image = annotation_image
        self.annotation_image_md5sum = annotation_image_md5sum

    @transaction.atomic
    def get_first_available_task(
        self,
        *,
        tags: Optional[List[str]] = None,
        exclude_tagged_for_others: bool = True,
    ) -> Optional[MarkingTask]:
        """Return the first marking task with a 'todo' status, sorted by `marking_priority`.

        If ``question`` and/or ``version``, restrict tasks appropriately.

        If ``tag`` is set, we restrict to papers with matching tags.

        If ``min_paper_num`` and/or ``max_paper_num`` are set, paper numbers in this
        range (including end points) are required.

        The results are sorted by priority.
        If the priority is the same, defer to paper number and then question number.

        Keyword Args:
            tags: a list of tags that the task must match.
            exclude_tagged_for_others: don't return papers that are
                tagged for users other than the one in ``self.user``,
                true by default.  Note if a username is explicitly
                listed in ``tags`` that takes precidence.

        Returns:
            A reference to the first available task, or
            `None` if no such task exists.
        """
        available = MarkingTask.objects.filter(status=MarkingTask.TO_DO)

        if self.question:
            available = available.filter(question_number=self.question)

        if self.version:
            available = available.filter(question_version=self.version)

        if self.min_paper_num:
            available = available.filter(paper__paper_number__gte=self.min_paper_num)

        if self.max_paper_num:
            available = available.filter(paper__paper_number__lte=self.max_paper_num)

        if tags:
            available = available.filter(markingtasktag__text__in=tags)

        if exclude_tagged_for_others:
            users = User.objects.all()
            other_user_tags = [f"@{u}" for u in users if u != self.user]
            # anything explicitly in tags should not be filtered here
            if tags:
                other_user_tags = [x for x in other_user_tags if x not in tags]
            available = available.exclude(markingtasktag__text__in=other_user_tags)

        if not available.exists():
            return None

        first_task = available.order_by(
            "-marking_priority", "paper__paper_number", "question_number"
        ).first()
        self.task_pk = first_task.pk
        return first_task

    @transaction.atomic
    def get_task(self) -> MarkingTask:
        """Retrieve the relevant marking task using self.code or self.task_pk.

        Raises:
            ObjectDoesNotExist: paper or paper with that question does not exist,
                not raised directly but from ``get_latest_task``.
            ValueError:
        """
        if self.task_pk:
            return MarkingTask.objects.get(pk=self.task_pk)
        elif self.code:
            paper_number, question_number = mark_task.unpack_code(self.code)
            task_to_assign = mark_task.get_latest_task(paper_number, question_number)
            self.task_pk = task_to_assign.pk
            return task_to_assign
        else:
            raise ValueError("Cannot find task - no public key or code specified.")

    @transaction.atomic
    def assign_task_to_user(self) -> MarkingTask:
        """Assign a specific marking task to a user.

        Fails if the relevant task can't be found, or the task cannot be
        assigned to that user.
        """
        task_to_assign = self.get_task()

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

        return page_data.get_question_pages_list(paper_number, question_number)

    @transaction.atomic
    def get_tags(self) -> List[str]:
        """Return all the tags for a task."""
        task = self.get_task()
        return mark_tags.get_tag_texts_for_task(task)

    @transaction.atomic
    def mark_task(self):
        """Accept a marker's annotation and grade for a task."""
        task = self.get_task()

        # save annotation image
        if self.annotation_image is None:
            raise ValueError("Cannot find annotation image to save.")
        if self.annotation_image_md5sum is None:
            raise ValueError("Cannot find annotation image hash.")
        annotation_image = annotations.save_annotation_image(
            self.annotation_image_md5sum, self.annotation_image
        )

        # save annotation
        if self.annotation_data is None:
            raise ValueError("Cannot find annotation data.")
        if self.user is None:
            raise ValueError("Cannot find user.")
        elif self.user != task.assigned_user:
            raise RuntimeError("User cannot create annotation for this task.")
        annotations.save_annotation(
            task,
            self.marking_data["score"],
            self.marking_data["marking_time"],
            annotation_image,
            self.annotation_data,
        )

        mark_task.update_task_status(task, MarkingTask.COMPLETE)
