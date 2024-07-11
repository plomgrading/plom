# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019 Omer Angel
# Copyright (C) 2019, 2021-2024 Colin B. Macdonald
# Copyright (C) 2020-2022 Andrew Rechnitzer
# Copyright (C) 2021 Peter Lee

from __future__ import annotations

from contextlib import contextmanager
import math
import os
import string
import sys
from typing import Any, Sequence

import arrow


# ------------------------------------------------
# some time conversion tools put here nice and central


def datetime_to_json(timestamp):
    return arrow.get(timestamp).for_json()


def json_to_arrow(timestring):
    return arrow.get(timestring)


def utc_now_to_string():
    """Format the time now in UTC to a string with no spaces."""
    return arrow.utcnow().format("YYYY-MM-DD_HH:mm:ss_ZZ")


def utc_now_to_simple_string():
    return arrow.utcnow().format("YYYY-MM-DD [at] HH:mm ZZZ")


def local_now_to_simple_string():
    return arrow.utcnow().to("local").format("YYYY-MM-DD [at] HH:mm ZZZ")


def arrowtime_to_string(arrowtime):
    """Format a time as an Arrow object to a string with no spaces."""
    return arrowtime.format("YYYY-MM-DD_HH:mm:ss_ZZ")


def arrowtime_to_simple_string(arrowtime):
    return arrowtime.format("YYYY-MM-DD [at] HH:mm:ss")


def delta_time_strings(ta, tb):
    return arrow.get(ta) - arrow.get(tb)


def is_within_one_hour_of_now(timestamp):
    if arrow.get(timestamp) > arrow.utcnow().shift(hours=-1):
        return True
    else:
        return False


# ---------------------------------------------
# tools for printing lists and other miscellany
# ---------------------------------------------


def format_int_list_with_runs(
    L: Sequence[str | int],
    *,
    use_unicode: None | bool = None,
    zero_padding: None | int = None,
) -> str:
    """Replace runs in a list with a range notation.

    Args:
        L: a list of integers (or strings that can be converted to
            integers).  Need not be sorted (we will sort a copy).

    Keyword Args:
        use_unicode: by default auto-detect from UTF-8 in stdout encoding
            or a boolean value to force on/off.  If we have unicode, then
            en-dash is used instead of hyphen to indicate ranges.
        zero_padding: if specified, pad each integer with this many zeros.
            By default (or on ``None``) don't do that.

    Returns:
        A string with comma-separated list, with dashed range notations
        for contiguous runs.  For example: ``"1, 2-5, 10-45, 64"``.
    """
    if use_unicode is None:
        if "utf-8" in str(sys.stdout.encoding).casefold():
            use_unicode = True
        else:
            use_unicode = False
    dash = "\N{EN DASH}" if use_unicode else "-"
    L2 = _find_runs(sorted([int(x) for x in L]))
    L3 = _flatten_2len_runs(L2)
    z = zero_padding if zero_padding else 0
    L4 = [
        f"{x[0]:0{z}}{dash}{x[-1]:0{z}}" if isinstance(x, list) else f"{x:0{z}}"
        for x in L3
    ]
    return ", ".join(L4)


def _find_runs(S: list[int]) -> list[list[int]]:
    L = []
    prev = -math.inf
    run: list[int] = []
    for x in S:
        if x - prev == 1:
            run.append(x)
        else:
            run = [x]
            L.append(run)
        prev = x
    return L


def _flatten_2len_runs(L: list[Any]) -> list[Any]:
    L2 = []
    for x in L:
        if len(x) < 3:
            L2.extend(x)
        else:
            L2.append(x)
    return L2


def run_length_encoding(L: list[Any]) -> list[tuple[Any, int, int]]:
    """Do a run-length-encoding of a list, producing triplets value, start, end.

    Examples:
    >>> run_length_encoding([7, 2, 2, 2, 9, 3, 3, 3])
    [(7, 0, 1), (2, 1, 4), (9, 4, 5), (3, 5, 8)]

    >>> run_length_encoding(["a", "a", "a", "a"])
    [('a', 0, 4)]

    >>> run_length_encoding([])
    []
    """
    runs: list[tuple[Any, int, int]] = []
    if not L:
        return runs
    prev = L[0]
    start = 0
    for i, x in enumerate(L):
        if x != prev:
            runs.append((prev, start, i))
            start = i
            prev = x
    runs.append((prev, start, i + 1))
    return runs


def next_in_longest_subsequence(items: list[str]) -> str | None:
    """Guess next entry in the longest unordered contiguous subsequence.

    Args:
        items: an unordered list of strings.

    Returns:
        The next item in a longest subsequence or ``None`` if no
        subsequences are detected.

    Examples:
    >>> next_in_longest_subsequence(["(a)", "(b)"])
    '(c)'

    >>> next_in_longest_subsequence(["i.", "ii.", "iii."])
    'iv.'

    >>> next_in_longest_subsequence(["2", "1", "C", "(a)", "A", "B"])
    'D'


    >>> next_in_longest_subsequence(["2", "b", "c", "Z", "foo"])

    >>> next_in_longest_subsequence(["a.", "b)", "(c)"])
    'b.'

    Notes:
      * Behaviour in a tie not well-defined; you'll get one of them.
      * "(a), (b)" and "a., b." are different subsequences.
      * The sequences should not be longer than the alphabet.  Overly
        long sequences don't count, e.g., if you already have a-z, then
        that subsequence cannot be extended:

    >>> from string import ascii_lowercase
    >>> next_in_longest_subsequence(["Q1", "Q2", *ascii_lowercase])
    'Q3'
    """
    romans = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
    romans.extend(["x" + n for n in romans] + ["xx" + n for n in romans])
    smallints = range(1, 31)

    # Each sequence we search is an iterable who iterates are strings
    # (caution: ascii_lowercase is a string not a list).
    sequences = [
        string.ascii_lowercase,
        [f"{x}." for x in string.ascii_lowercase],
        [f"{x})" for x in string.ascii_lowercase],
        [f"({x})" for x in string.ascii_lowercase],
        string.ascii_uppercase,
        [f"{x}." for x in string.ascii_uppercase],
        [f"{x})" for x in string.ascii_uppercase],
        [f"({x})" for x in string.ascii_uppercase],
        romans,
        [f"{x}." for x in romans],
        [f"{x})" for x in romans],
        [f"({x})" for x in romans],
        [f"Q{x}" for x in smallints],
        [f"{x}." for x in smallints],
        [f"{x}" for x in smallints],
    ]

    counts = [0] * len(sequences)
    for idx, seq in enumerate(sequences):
        for count, x in enumerate(seq):
            if x not in items:
                counts[idx] = count
                break

    idx, n = max(enumerate(counts), key=lambda t: t[1])

    if n > 0:
        return sequences[idx][n]

    return None


@contextmanager
def working_directory(path):
    """Temporarily change the current working directory.

    Usage:
    ```
    with working_directory(path):
        do_things()   # working in the given path
    do_other_things() # back to original path
    ```
    """
    current_directory = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(current_directory)


def interpolate_questions_over_pages(
    pages: int, questions: int, *, firstpg: int = 1
) -> list[list[int]]:
    """Fit a number of pages to a number of questions, returning a list of lists of which pages go with each question.

    This function is intended to be used to provide an initial guess
    of how to map the pages to questions.

    Args:
        pages: how many pages.
        questions: how many questions.

    Keyword Args:
        firstpg: what is the first page?

    Returns:
        A list of lists representing the pages occupied by each question.
    """
    if pages == questions:
        question_pages = [[p + firstpg] for p in range(pages)]
    elif pages < questions:
        # shared pages
        qpp = questions // pages
        remainder = questions % pages
        X = []
        for pg in range(pages):
            how_many = qpp
            if remainder:
                # spread the remainder over the first few pages
                how_many += 1
                remainder -= 1
            X.extend([[pg + firstpg]] * how_many)
        return X
    else:
        # Some question span multiple pages.
        # Evenly divide the pages as much as possible
        ppq = pages // questions
        question_pages = [
            [q * ppq + pn + firstpg for pn in range(ppq)] for q in range(questions)
        ]
        # then put any remaining pages to the last question
        question_pages[-1] = [
            pn for pn in range(question_pages[-1][0], pages + firstpg)
        ]
        # TODO: could instead spread them over the last few questions
    return question_pages
