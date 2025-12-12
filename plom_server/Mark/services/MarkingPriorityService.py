# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2025 Aidan Murphy

"""Functions for setting and modifying priority for marking tasks.

See also the closely-related
:class:`plom_server.TaskOrder.services.TaskOrderService`.
"""

import random

from django.db import transaction
from django.db.models import QuerySet, OuterRef, Subquery
from django.db.models.functions import Random

from plom_server.Base.services import Settings
from plom_server.Papers.models import Paper
from ..models import MarkingTask


def get_mark_priority_strategy() -> str:
    """Return the current priority strategy for marking tasks."""
    return Settings.key_value_store_get("task_order_strategy")


def _get_tasks_to_update_priority() -> QuerySet[MarkingTask]:
    """Get all the relevant marking tasks for updating priority.

    When the priority strategy is changed, all tasks that have
    TO_DO status are updated, and all tasks with other statuses -
    OUT_OF_DATE, OUT, COMPLETE - keep their old priority values.
    """
    tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO)
    return tasks.select_related("paper")


def get_tasks_to_update_priority_by_q_v(
    question_idx: int, version: int
) -> QuerySet[MarkingTask]:
    """Get all the relevant marking tasks with given q,v for updating priority."""
    tasks = _get_tasks_to_update_priority().filter(
        question_index=question_idx, question_version=version
    )
    return tasks.select_related("paper")


@transaction.atomic
def set_marking_priority_shuffle() -> None:
    """Set the priority to shuffle: every marking task gets a random priority value.

    All work happens on the DB side. Take care when editing this function and
    consider performance at scale.

    Note: logic here is repeated in :function:`compute_priority` which
    is used in `marking_task_service.py`.  Make sure you change both if
    you make changes here.
    """
    tasks = _get_tasks_to_update_priority()
    # this bit constructs an SQL query. All work happens within the DB.
    tasks.update(marking_priority=Random() * 1000)
    Settings.key_value_store_set("task_order_strategy", "shuffle")


def compute_priority(
    papernum: int, *, strategy: str | None = None, largest_paper_num: int | None = None
) -> int:
    """Compute the priority for a new task.

    Args:
        papernum: some calculations rely on the paper number.

    Keyword Args:
        strategy: which strategy should we use for the calculation?
            If omitted we can query the database.
        largest_paper_num: some calculations need to know this.  If
            not provided, we will query the database but you may
            wish to provide it for efficiency if you're calling about
            multiple tasks.

    Note: logic is repeated elsewhere in this file, be careful making
    changes to ensure consistency.
    """
    if strategy is None:
        strategy = get_mark_priority_strategy()
    if strategy == "paper_number":
        if largest_paper_num is None:
            largest_paper_num = (
                Paper.objects.all().order_by("-paper_number").first().paper_number
            )
        priority = largest_paper_num - papernum
    else:
        # TODO: careful this 1000 is also repeated elsewherre.
        priority = random.randint(0, 1000)
    # in case of bugs, priority should always be positive, for some unknonn
    # reason that would be revisited.
    priority = max(0, priority)
    return priority


@transaction.atomic
def set_marking_priority_paper_number() -> None:
    """Set the priority inversely proportional to the paper number.

    Some complex Django expressions to ensure most processing happens
    on the db side. Take care when editing this and consider
    performance at scale.

    Note: logic here is repeated in :function:`compute_priority` which
    is used in `marking_task_service.py`.  Make sure you change both if
    you make changes here.
    """
    # See issue #4096
    largest_paper_num = (
        Paper.objects.all().order_by("-paper_number").first().paper_number
    )
    tasks = _get_tasks_to_update_priority()

    # this subquery is a workaround for an UPDATE with a JOIN statement
    # (not allowed in Django)
    # it reads something like 'JOIN PAPER on OUTERTABLE.paper=PAPER.id'
    # where OUTERTABLE isn't specified until the subquery is embedded
    # in a different Django expression.
    papernum_subquery = Paper.objects.filter(id=OuterRef("paper")).values(
        "paper_number"
    )

    tasks.update(marking_priority=largest_paper_num - Subquery(papernum_subquery))
    Settings.key_value_store_set("task_order_strategy", "paper_number")


@transaction.atomic
def set_marking_priority_custom(
    custom_order: dict[tuple[int, int], int | float],
) -> None:
    """Set the priority to a custom ordering.

    Args:
        custom_order: dict with tuple keys representing (paper_number, question_index)
            and values representing the task's custom priority. If a task is not included
            in custom_order, it remains the same. If the key is valid, but the corresponding
            task doesn't exist, the entry is ignored.
    """
    assert isinstance(
        custom_order, dict
    ), "`custom_order` must be of type dict[tuple[int, int], int]."

    tasks = _get_tasks_to_update_priority()
    tasks_to_update = []
    for k, v in custom_order.items():
        paper_number, question_index = k
        if tasks.filter(
            paper__paper_number=paper_number,
            question_index=question_index,
        ).exists():
            task_to_update = tasks.get(
                paper__paper_number=paper_number, question_index=question_index
            )
            task_to_update.marking_priority = v
            tasks_to_update.append(task_to_update)
    MarkingTask.objects.bulk_update(tasks_to_update, ["marking_priority"])
    Settings.key_value_store_set("task_order_strategy", "custom")


def modify_task_priority(task: MarkingTask, new_priority: int | float) -> None:
    """Modify the priority of a single marking task."""
    task.marking_priority = new_priority
    task.save()
