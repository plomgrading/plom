# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020, 2023 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald

from __future__ import annotations

import ast
from typing import Any


def _parse_questions(s: Any) -> Any:
    if isinstance(s, str):
        if s.casefold() == "all":
            return "all"
        s = ast.literal_eval(s)
    return s


def check_question_list(s: str | list | tuple, n_questions: int) -> list[int]:
    """Make a canonical list of questions.

    Args:
        s (str/list/tuple): the input, can be a special string "all"
            or a string which we will parse.  Or an integer.  Or a list
            of ints.
        n_questions (int): how many questions total, used for checking
            input.

    Returns:
        list:
    """
    s = _parse_questions(s)
    if s == "all":
        s = list(range(1, n_questions + 1))

    question_list = s
    del s

    if isinstance(question_list, str):
        raise ValueError('question cannot be a string, unless its "all"')

    if isinstance(question_list, int):
        question_list = [question_list]
    if not isinstance(question_list, list):
        raise ValueError("The question list must be a valid python list")

    for q in question_list:
        if isinstance(q, int):
            if q < 1 or q > n_questions:
                raise ValueError(
                    f"Question numbers must be integers between 1 and {n_questions} (inclusive)"
                )
        else:
            raise ValueError(
                f"Question numbers must be integers between 1 and {n_questions} (inclusive)"
            )
    # TODO: would we like an explicit error on dupes?
    return list(set(question_list))


def canonicalize_page_question_map(
    # s: str | int | list[int] | list[list[int]],
    s: Any,
    pages: int,
    numquestions: int,
) -> list[list[int]]:
    """Make a canonical page-to-questions mapping from various shorthand inputs.

    Args:
        s: the input, can be a special string "all"
            or a string which we will parse.  Or an integer.  Or a list
            of ints, or a list of list of ints.
            So many types of input are supported, that its a bit tricky
            to specify formal "typing"; currently set to ``All``.
        pages: how many pages, used for checking input.
        numquestions: how many questions total, used for checking input.

    Returns:
        A list of lists.
    """
    s = _parse_questions(s)
    if s == "all":
        s = range(1, numquestions + 1)

    if isinstance(s, str):
        raise ValueError('question cannot be a string, unless its "all"')

    if isinstance(s, int):
        s = [s]

    if isinstance(s, dict):
        raise NotImplementedError("a dict seems very sensible but is not implemented")

    # TypeError if not iterable
    iter(s)

    # are the contents themselves iterable?
    try:
        iter(s[0])
    except TypeError:
        # if not, repeat the list for each page
        s = [s] * pages

    if len(s) != pages:
        raise ValueError(f"list too short: need one list for each of {pages} pages")

    # cast to lists (and pass through sets to de-dupe)
    s = [list(set(qlist)) for qlist in s]

    # finally we should have a canonical list-of-lists-of-ints
    for qlist in s:
        for qnum in qlist:
            if not isinstance(qnum, int):
                raise ValueError(f"non-integer question value {qnum}")
            if qnum < 1 or qnum > numquestions:
                raise ValueError(f"question value {qnum} outside [1, {numquestions}]")
    return s
