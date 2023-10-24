# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

"""Services for data related to specific marking tasks."""

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from Papers.models import Paper
from ..models import MarkingTask


@transaction.atomic
def get_latest_task(paper_number: int, question_number: int) -> MarkingTask:
    """Get a marking task from its paper number and question number.

    Args:
        paper_number: int
        question_number: int

    Returns:
        The MarkingTask.

    Raises:
        ObjectDoesNotExist: no such marking task, either b/c the paper
            does not exist or the question does not exist for that paper.
    """
    try:
        paper = Paper.objects.get(paper_number=paper_number)
    except ObjectDoesNotExist as e:
        # reraise with a more detailed error message
        raise ObjectDoesNotExist(
            f"Task for paper {paper_number} question {question_number} does not exist"
        ) from e
    r = (
        MarkingTask.objects.filter(paper=paper, question_number=question_number)
        .order_by("-time")
        .first()
    )
    # Issue #2851, special handling of the None return
    if r is None:
        raise ObjectDoesNotExist(
            f"Task does not exist: we have paper {paper_number} but "
            f"not question index {question_number}"
        )
    return r


@transaction.atomic
def unpack_code(code: str) -> tuple[int, int]:
    """Return a tuple of (paper_number, question_number) from a task code string.

    Args:
        code (str): a task code, e.g. q0001g1. Requires code to be at least 4 characters
        long. Requires code to start with "q" and contain a "g" somewhere after the second
        character, but not be the last character and the rest of the characters to be numeric.
    """
    assert len(code) >= len("q0g0")
    assert code[0] == "q"

    split_index = code.find("g", 2)

    # g must be present
    assert split_index != -1
    # g cannot be the last character
    assert split_index != len(code) - 1

    paper_number = int(code[1:split_index])
    question_number = int(code[split_index + 1 :])

    return paper_number, question_number


@transaction.atomic
def update_task_status(
    task: MarkingTask, status: MarkingTask.StatusChoices
) -> MarkingTask:
    """Set the status of a marking task.

    Args:
        task: reference to a marking task
        status: one of the MarkingTask.StatusChoices enum options

    Returns:
        Updated task instance
    """
    task.status = status
    task.save()
    return task
