# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023 Natalie Balashov

"""Services for data related to specific marking tasks."""

from django.core.exceptions import ObjectDoesNotExist

from ..models import MarkingTask


def get_latest_task(
    paper_number: int, question_idx: int, *, question_version: int | None = None
) -> MarkingTask:
    """Get a marking task from its paper number and question index, and optionally version.

    No locks are held or atomic operations made, nor select for update:
    this is a low-level routine.  Apply whatever safeguards you need in
    the caller.

    We prefetch the ``assigned_user`` fields as some callers want that.

    Args:
        paper_number: which paper.
        question_idx: which question, by 1-based question index.

    Keyword Args:
        question_version: which version, or None/omit to ignore versions.

    Returns:
        The MarkingTask object.

    Raises:
        ObjectDoesNotExist: no such marking task, either b/c the paper
            does not exist or the question does not exist for that paper.
        ValueError: that paper/question pair does exist but not with the
            specified version.
    """
    r = (
        MarkingTask.objects.filter(
            paper__paper_number=paper_number, question_index=question_idx
        )
        .prefetch_related("assigned_user")
        .order_by("-time")
        .first()
    )
    if r is None:
        raise ObjectDoesNotExist(
            f"Task for paper number {paper_number}"
            f" question index {question_idx} does not exist"
        )
    if question_version is not None:
        if r.question_version != question_version:
            raise ValueError(
                f"Task for paper {paper_number} question index {question_idx} "
                f"exists with version {r.question_version} not {question_version}."
                "  You're likely asking for the wrong version."
            )
    return r


def unpack_code(code: str) -> tuple[int, int]:
    """Return a tuple of (paper_number, question_index) from a task code string.

    Args:
        code: a task code which is a string like "0001g1".  Requires code to be
            at least 3 characters long.  For legacy reasons, code can optionally
            start with a "q" which will be discarded.
            Requires that code contain a "g" somewhere after the first character,
            but not be the last character and the rest of the characters to be
            numeric.

    Returns:
        A tuple of two integers, the paper number and the question index.

    Raises:
        ValueError: described conditions are not satisfied.
    """
    if code.startswith("q"):
        code = code[1:]

    errbase = f'invalid task code "{code}": '
    if len(code) < len("0g0"):
        raise ValueError(errbase + "too short")

    if "g" not in code:
        raise ValueError(errbase + 'must contain a "g"')

    left, right = code.split("g")

    try:
        paper_number = int(left)
    except ValueError as e:
        raise ValueError(errbase + f"cannot get paper_number: {e}") from None

    try:
        question_idx = int(right)
    except ValueError as e:
        raise ValueError(errbase + f"cannot get question_idx: {e}") from None

    return paper_number, question_idx
