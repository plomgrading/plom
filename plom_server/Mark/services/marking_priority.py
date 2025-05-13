# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

"""Functions for setting and modifying priority for marking tasks."""

import random

from django.db import transaction
from django.db.models import QuerySet

from plom_server.Papers.models import Paper
from ..models import MarkingTask, MarkingTaskPriority


@transaction.atomic
def get_mark_priority_strategy() -> MarkingTaskPriority.StrategyChoices:
    """Return the current priority strategy for marking tasks."""
    return MarkingTaskPriority.load().strategy


@transaction.atomic
def is_priority_modified() -> bool:
    """Return the priority's modified property."""
    return MarkingTaskPriority.load().modified


@transaction.atomic
def get_tasks_to_update_priority() -> QuerySet[MarkingTask]:
    """Get all the relevant marking tasks for updating priority.

    When the priority strategy is changed, all tasks that have
    TO_DO status are updated, and all tasks with other statuses -
    OUT_OF_DATE, OUT, COMPLETE - keep their old priority values.
    """
    tasks = MarkingTask.objects.filter(status=MarkingTask.TO_DO)
    return tasks.select_related("paper")


@transaction.atomic
def set_marking_priority_strategy(strategy: MarkingTaskPriority.StrategyChoices):
    """Set the current priority strategy; as a side-effect, set the modified status to False."""
    assert strategy in MarkingTaskPriority.StrategyChoices, "Invalid priority value."

    priority = MarkingTaskPriority.load()
    priority.strategy = strategy
    priority.modified = False
    priority.save()


@transaction.atomic
def set_marking_piority_shuffle():
    """Set the priority to shuffle: every marking task gets a random priority value."""
    tasks = get_tasks_to_update_priority()
    for task in tasks:
        task.marking_priority = random.randint(0, 1000)

    MarkingTask.objects.bulk_update(tasks, ["marking_priority"])
    set_marking_priority_strategy(MarkingTaskPriority.SHUFFLE)


@transaction.atomic
def set_marking_priority_paper_number():
    """Set the priority inversely proportional to the paper number."""
    largest_paper_num = (
        Paper.objects.all().order_by("-paper_number").first().paper_number
    )
    tasks = get_tasks_to_update_priority()
    for task in tasks:
        task.marking_priority = largest_paper_num - task.paper.paper_number
    MarkingTask.objects.bulk_update(tasks, ["marking_priority"])
    set_marking_priority_strategy(MarkingTaskPriority.PAPER_NUMBER)


@transaction.atomic
def set_marking_priority_custom(custom_order: dict[tuple[int, int], int]):
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

    tasks = get_tasks_to_update_priority()
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
    set_marking_priority_strategy(MarkingTaskPriority.CUSTOM)


@transaction.atomic
def modify_task_priority(task: MarkingTask, new_priority: int):
    """Modify the priority of a single marking task.

    If successful, set MarkingTaskPriority.modified to true.
    """
    task.marking_priority = new_priority
    task.save()
    priority_setting = MarkingTaskPriority.load()
    priority_setting.modified = True
    priority_setting.save()
