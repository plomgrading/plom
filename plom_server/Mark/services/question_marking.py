# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from __future__ import annotations

from typing import Any

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.auth.models import User
from django.db import transaction

from ..models import MarkingTask
from . import mark_task
from . import create_new_annotation_in_database


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

    @staticmethod
    @transaction.atomic
    def get_first_available_task(
        *,
        question_idx: int | None = None,
        version: int | None = None,
        user: User | None = None,
        min_paper_num: int | None = None,
        max_paper_num: int | None = None,
        tags: list[str] | None = None,
        exclude_tagged_for_others: bool = True,
    ) -> MarkingTask | None:
        """Return the first marking task with a 'todo' status, sorted by `marking_priority`.

        If ``question`` and/or ``version``, restrict tasks appropriately.

        If ``min_paper_num`` and/or ``max_paper_num`` are set, paper numbers in this
        range (including end points) are required.

        The results are sorted by priority.
        If the priority is the same, defer to paper number and then question index.

        Keyword Args:
            question_idx: optional question index for the task.
            version: optional question version for the task.
            user: reference to a user instance, used to filter out
                tasks that are tagged for someone else.
            min_paper_num: optional minimum paper number of the task.
            max_paper_num: optional maximum paper number of the task.
            tags: a task must match at least one of the strings in this
                list.
            exclude_tagged_for_others: don't return papers that are
                tagged for users other than the one in ``self.user``,
                true by default.  Note if a username is explicitly
                listed in ``tags`` that takes precedence.

        Returns:
            A reference to the first available task, or
            `None` if no such task exists.
        """
        available = MarkingTask.objects.filter(status=MarkingTask.TO_DO)

        if question_idx:
            available = available.filter(question_index=question_idx)

        if version:
            available = available.filter(question_version=version)

        if min_paper_num:
            available = available.filter(paper__paper_number__gte=min_paper_num)

        if max_paper_num:
            available = available.filter(paper__paper_number__lte=max_paper_num)

        if tags:
            available = available.filter(markingtasktag__text__in=tags)

        if exclude_tagged_for_others:
            users = User.objects.all()
            other_user_tags = [f"@{u}" for u in users if u != user]
            # anything explicitly in tags should not be filtered here
            if tags:
                other_user_tags = [x for x in other_user_tags if x not in tags]
            available = available.exclude(markingtasktag__text__in=other_user_tags)

        if not available.exists():
            return None

        first_task = available.order_by(
            "-marking_priority", "paper__paper_number", "question_index"
        ).first()
        return first_task

    def _get_task_for_update(self) -> MarkingTask:
        """Retrieve the relevant marking task using self.code or self.task_pk, and select it for update.

        Raises:
            ObjectDoesNotExist: paper or paper with that question does not exist,
                not raised directly but from ``get_latest_task``.
            ValueError:
        """
        if self.task_pk:
            return MarkingTask.objects.select_for_update().get(pk=self.task_pk)
        elif self.code:
            paper_number, question_index = mark_task.unpack_code(self.code)
            task_to_assign = mark_task.get_latest_task(paper_number, question_index)
            self.task_pk = task_to_assign.pk
            return self._get_task_for_update()
        else:
            raise ValueError("Cannot find task - no public key or code specified.")

    @staticmethod
    @transaction.atomic
    def mark_task(
        code: str,
        *,
        user: User,
        marking_data: dict[str, Any],
        annotation_data: dict,
        annotation_image: InMemoryUploadedFile,
        annotation_image_md5sum: str,
    ) -> None:
        """Accept a marker's annotation and grade for a task, store them in the database.

        Not implemented yet: 406: integrity fail; 410 for task deleted

        Raises:
            RuntimeError: not the assigned user.
            ValueError: anything related to a poorly formed bad request,
                such as invalid code, or wrong image format.
        """
        try:
            papernum, question_idx = mark_task.unpack_code(code)
        except AssertionError as e:
            raise ValueError(e) from e

        # TODO: ObjectDoesNotExist, not ValueError (only with version checks)
        task = mark_task.get_latest_task(papernum, question_idx)

        if user != task.assigned_user:
            raise RuntimeError(
                "User cannot create annotation for this task:"
                " perhaps task has been reassigned"
            )

        # Various work in creating the new Annotation object: linking it to the
        # associated Rubrics and managing the task's latest annotation link.
        create_new_annotation_in_database(
            task,
            marking_data["score"],
            marking_data["marking_time"],
            annotation_image_md5sum,
            annotation_image,
            annotation_data,
        )
        # Note the helper function above also performs `task.save`; that seems ok.
        task.status = MarkingTask.COMPLETE
        task.save()
