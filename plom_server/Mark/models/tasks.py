# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2025 Aidan Murphy

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from plom_server.Base.models import Tag
from plom_server.Papers.models import Paper


class MarkingTask(models.Model):
    """Represents a single question that needs to be marked.

    paper: reference to Paper, the test-paper of the question
    code: str, a unique string for indexing a marking task
    question_index: int, the question to mark
    question_version: int, the version of the question
    latest_annotation: reference to Annotation, the latest annotation for this task
    marking_priority: float, the priority of this task.
        Default is 0, but when MarkingTask instances are created with
        MarkingTaskService.create_task(), the default is replaced with
        a value determined by the current server settings.

    assigned_user: reference to User, the user currently attached to
        the task.  Can be null, can change over time. Notice that when
        a tasks has status "out" or "complete" then it must have an
        assigned_user, and when it is set to "to do" or "out of date"
        it must have assigned_user set to none.
    time: the time the task was originally created.
        TODO: is this used for anything?
    last_update: the time of the last update to the task (updated whenever model is saved)
    status: str, represents the status of the task: not started, sent
        to a client, completed, out of date.

    Status
    ~~~~~~

    MarkingTasks have a status, represented by a choice kwarg, see
    https://docs.djangoproject.com/en/4.2/ref/models/fields/#choices
    for more info.  Specifically:

      - `StatusChoices.TO_DO`: No user has started work on this task.
      - `StatusChoices.OUT`: Some user has this task signed out.  If they
        surrender the task later, it goes back to being TO_DO.
        You can find out who it is assigned to by checking the
        "assigned_user" field.
      - `StatusChoices.COMPLETE`: The task is finished.  However the
        new annotations associated with it could arrive: this is tracked
        via idea of the "Latest Annotation".
      - `StatusChoices.OUT_OF_DATE`: various actions could invalidate
        the work, such as removing a Page, or adding a new one.  In this
        case the task becomes out-of-date, in lieu of being deleted.
        It cannot transition back to earlier states.
        OUT_OF_DATE can still have a Latest Annotation.

    Note: Another table, :class:`PaperIDTask`, shares similar status
    choices and some other fields; once upon a time they shared a common
    subclass.
    """

    StatusChoices = models.IntegerChoices("Status", "TO_DO OUT COMPLETE OUT_OF_DATE")
    TO_DO = StatusChoices.TO_DO
    OUT = StatusChoices.OUT
    COMPLETE = StatusChoices.COMPLETE
    OUT_OF_DATE = StatusChoices.OUT_OF_DATE

    assigned_user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time = models.DateTimeField(default=timezone.now)
    status = models.IntegerField(
        null=False, choices=StatusChoices.choices, default=TO_DO
    )
    last_update = models.DateTimeField(auto_now=True)

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    code = models.TextField(default="", unique=False)
    question_index = models.PositiveIntegerField(null=False, default=0)
    question_version = models.PositiveIntegerField(null=False, default=0)
    latest_annotation = models.OneToOneField(
        "Annotation", unique=True, null=True, on_delete=models.SET_NULL
    )
    marking_priority = models.FloatField(null=False, default=0.0)

    def __str__(self):
        """Return information about the paper and the question."""
        return (
            f"MarkingTask (paper={self.paper.paper_number}, "
            f"question_index={self.question_index})"
        )


class MarkingTaskTag(Tag):
    """Represents a tag that can be assigned to one or more marking tasks."""

    task = models.ManyToManyField(MarkingTask)
