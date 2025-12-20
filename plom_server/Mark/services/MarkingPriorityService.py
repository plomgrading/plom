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
from django.db.models import QuerySet

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


def modify_task_priority(task: MarkingTask, new_priority: int | float) -> None:
    """Modify the priority of a single marking task."""
    task.marking_priority = new_priority
    task.save()


def update_priority_ordering(
    order: str,
    *,
    custom_order: None | dict[tuple[int, int], int | float] = None,
) -> None:
    """Update the priority ordering of tasks.

    Args:
        order: one of "shuffle", "paper_number", or "custom".

    Keyword Args:
        custom_order: a dictionary specifying a custom task ordering
            (for existing tasks).
    """
    if order == "shuffle":
        set_marking_priority_shuffle()
    elif order == "custom":
        assert custom_order is not None, "must provide custom_order kwarg"
        set_marking_priority_custom(custom_order=custom_order)
    elif order == "paper_number":
        set_marking_priority_paper_number()
    else:
        raise RuntimeError(f"'{order}' is not a valid option for 'order'")


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
    pq_pairs_queryset = tasks.values_list("paper__paper_number", "question_index")
    priority_dict = {}
    for pq_pair in pq_pairs_queryset:
        priority_dict.update(
            {pq_pair: compute_priority(pq_pair[0], strategy="shuffle")}
        )

    set_marking_priority_custom(priority_dict)
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
        priority = random.random() * 1000
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
    pq_pairs_queryset = tasks.values_list("paper__paper_number", "question_index")

    priority_dict = {}
    for pq_pair in pq_pairs_queryset:
        papernum = pq_pair[0]
        priority = compute_priority(
            papernum, strategy="paper_number", largest_paper_num=largest_paper_num
        )
        priority_dict.update({pq_pair: priority})

    set_marking_priority_custom(priority_dict)
    Settings.key_value_store_set("task_order_strategy", "paper_number")


@transaction.atomic
def set_marking_priority_custom(
    custom_order: dict[tuple[int, int], int | float],
) -> None:
    """Set the priority of marking tasks to a custom ordering.

    Consider performance at scale when changing this function.

    Args:
        custom_order: dict with tuple keys representing (paper_number, question_index)
            and values representing the task's custom priority. If a task is not included
            in custom_order, it remains the same. If the key is valid, but the corresponding
            task doesn't exist, the entry is ignored.
    """
    assert isinstance(
        custom_order, dict
    ), "`custom_order` must be of type dict[tuple[int, int], int]."

    tasks_to_update = _get_tasks_to_update_priority()

    # Between the custom_order dict and the db rows, we must iterate over one,
    # and use the other as a lookup table.
    # Use the custom_order dict as the lookup table, **not** the db rows.
    for task in tasks_to_update:
        try:
            task.marking_priority = custom_order[
                (task.paper.paper_number, task.question_index)
            ]
        except KeyError:
            # caller didn't specify a priority for this task, so do nothing
            pass

    MarkingTask.objects.bulk_update(
        tasks_to_update, ["marking_priority"], batch_size=1000
    )
    Settings.key_value_store_set("task_order_strategy", "custom")
