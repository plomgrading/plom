# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

from django.db import models

from Base.models import BaseTask, Tag, SingletonBaseModel
from Papers.models import Paper


class MarkingTask(BaseTask):
    """Represents a single question that needs to be marked.

    paper: reference to Paper, the test-paper of the question
    code: str, a unique string for indexing a marking task
    question_number: int, the question to mark
    question_version: int, the version of the question
    latest_annotation: reference to Annotation, the latest annotation for this task
    marking_priority: int, the priority of this task.
        Default is 0, but upon initialization of the MarkingTask,
        it is set to a random int between 0 and 1000.

    Status
    ~~~~~~

    Inherited from the superclass, MarkingTasks also have a status:

      - `StatusChoices.TO_DO`: No user has started work on this task.
      - `StatusChoices.OUT`: Some user has this task signed out.  If they
        surrender the task later, it goes back to being TO_DO.
      - `StatusChoices.COMPLETE`: The task is finished.  However the
        new annotations associated with it could arrive: this is tracked
        via idea of the "Latest Annotation".
      - `StatusChoices.OUT_OF_DATE`: various actions could invalidate
        the work, such as removing a Page, or adding a new one.  In this
        case the task becomes out-of-date, in lieu of being deleted.
        It cannot transition back to earlier states.
        OUT_OF_DATE can still have a Latest Annotation.
    """

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    code = models.TextField(default="", unique=False)
    question_number = models.PositiveIntegerField(null=False, default=0)
    question_version = models.PositiveIntegerField(null=False, default=0)
    latest_annotation = models.OneToOneField(
        "Annotation", unique=True, null=True, on_delete=models.SET_NULL
    )
    marking_priority = models.PositiveIntegerField(null=False, default=0)

    def __str__(self):
        """Return information about the paper and the question."""
        return f"MarkingTask (paper={self.paper.paper_number}, question={self.question_number})"


class MarkingTaskPriority(SingletonBaseModel):
    """Represents the current strategy for ordering tasks.

    Strategy is an enum of PAPER_NUMBER, SHUFFLE, or CUSTOM. The state of
    MarkingTaskPriority.load().strategy determines if the marking task
    priority is random, based on paper number, or custom. If custom,
    the priority will be based on the dict stored in the custom_priority field.
    """

    StrategyChoices = models.IntegerChoices("Strategy", "PAPER_NUMBER SHUFFLE CUSTOM")
    PAPER_NUMBER = StrategyChoices.PAPER_NUMBER
    SHUFFLE = StrategyChoices.SHUFFLE
    CUSTOM = StrategyChoices.CUSTOM

    strategy = models.IntegerField(
        null=False, choices=StrategyChoices.choices, default=PAPER_NUMBER
    )
    modified = models.BooleanField(default=False, null=False)


class MarkingTaskTag(Tag):
    """Represents a tag that can be assigned to one or more marking tasks."""

    task = models.ManyToManyField(MarkingTask)
