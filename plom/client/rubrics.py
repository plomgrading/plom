# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald


from plom.plom_exceptions import PlomInconsistentRubricsException


def compute_score_naive(rubrics, maxscore):
    """Compute score given a set of rubrics, using naive straight sum rules.

    args:
        rubrics (list):
        maxscore (int): the maximum anticipated score

    returns:
        int: the computed score

    raises:
        ValueError: int is outside range [0, maxscore].

    This is probably the simplest scoring system: literally
    just add/subject the values of each rubric.  Likely too
    simple for actual use.
    """
    score = 0
    for r in rubrics:
        if r["kind"] != "neutral":
            # neutral should have value 0, but doesn't hurt
            score += int(r["value"])
    if score < 0 or score > maxscore:
        raise ValueError("score is out of range")
    return score


def compute_score_legacy2022(rubrics, maxscore):
    """Compute score given a set of rubrics, using "Plom 2022" rules.

    args:
        rubrics (list):
        maxscore (int): the maximum anticipated score

    returns:
        int: the computed score

    raises:
        PlomInconsistentRubricsException: for example, absolute and
            relative rubrics cannot be mixed.
        ValueError: int is outside range [0, maxscore], or non-zero,
            non-full marks absolute rubrics in use.

    Tries to follow the rules as used in 2022, as closely as possible.
    """
    score = 0

    absolutes = [r for r in rubrics if r["kind"] == "absolute"]
    if len(absolutes) > 1:
        raise PlomInconsistentRubricsException("Can use at most one absolute rubric")

    for r in absolutes:
        if int(r["value"]) not in (0, maxscore):
            raise ValueError("legacy2022 allows only 0 or full-mark absolute rubrics")
        score += int(r["value"])

    # next, decide if up or down (not both) and adjust
    uppers = [
        int(r["value"])
        for r in rubrics
        if r["kind"] == "relative" and int(r["value"]) > 0
    ]
    downrs = [
        int(r["value"])
        for r in rubrics
        if r["kind"] == "relative" and int(r["value"]) < 0
    ]

    if uppers and downrs:
        raise PlomInconsistentRubricsException("Cannot mix up and down deltas")
    if len(absolutes) > 0 and (uppers or downrs):
        raise PlomInconsistentRubricsException("Cannot relative and absolute rubrics")

    if uppers:
        score = sum(uppers)
    if downrs:
        score = maxscore + sum(downrs)

    if score < 0 or score > maxscore:
        raise ValueError("score is out of range")
    return score


# compute_score = compute_score_naive
compute_score = compute_score_legacy2022


def is_ambiguous(rubrics, maxscore):
    """TODO

    rough idea: returns false for mixed up/down?
    """
    pass
