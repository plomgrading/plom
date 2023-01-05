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
        None/int: the computed score or `None` if there are no mark-changing
        annotations on the page.  Note `None` is different from `0`.

    raises:
        PlomInconsistentRubricsException: for example, absolute and
            relative rubrics cannot be mixed.
        ValueError: int is outside range [0, maxscore], or non-zero,
            non-full marks absolute rubrics in use.

    Tries to follow the rules as used in 2022, as closely as possible.
    """
    score = None

    absolutes = [r for r in rubrics if r["kind"] == "absolute"]
    if len(absolutes) > 1:
        raise PlomInconsistentRubricsException("Can use at most one absolute rubric")

    for r in absolutes:
        if int(r["value"]) not in (0, maxscore):
            raise ValueError("legacy2022 allows only 0 or full-mark absolute rubrics")
        if score is None:
            score = 0
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

    if score is not None and (score < 0 or score > maxscore):
        raise ValueError("score is out of range")
    return score


def compute_score_locabs(rubrics, maxscore):
    """Compute score given a set of rubrics.

    A new set of rubric summation rules, designed to allow mixing up
    "locally absolute" rubrics for per-part marking, combined with
    +/- rubrics when they are unambiguous.

    args:
        rubrics (list):
        maxscore (int): the maximum anticipated score

    returns:
        None/int: the computed score or `None` if there are no mark-changing
        annotations on the page.  Note `None` is different from `0`.

    raises:
        PlomInconsistentRubricsException: for example, absolute and
            relative rubrics cannot be mixed.
        ValueError: int is outside range [0, maxscore], or absolute rubrics
            are out of their own range ``[0, out_of]``.  Can also be because
            the total of all ``out_of`` are more than maxscore.  The absolute
            rubrics give upper/lower bounds for possible scores which raise
            ValueErrors if exceeded by relative rubrics.
    """
    lo_score = 0
    hi_score = maxscore
    sum_out_of = 0

    # step one: add up all the absolute rubrics
    absolutes = [r for r in rubrics if r["kind"] == "absolute"]

    for r in absolutes:
        out_of = r["out_of"]
        if out_of not in range(1, maxscore + 1):
            # TODO: or Inconsistent?
            raise ValueError(f"out_of is outside of [1, {maxscore}]")
        if r["value"] not in range(0, out_of + 1):
            # TODO: or Inconsistent?
            raise ValueError(f"value is outside of [0, out_of] where out_of={out_of}")
        lo_score += r["value"]
        hi_score -= r["out_of"] - r["value"]
        sum_out_of += out_of

    if sum_out_of > maxscore:
        # TODO: or Inconsistent?
        raise ValueError(f"sum of out_of is outside [0, {maxscore}]")

    uppers = [r for r in rubrics if r["kind"] == "relative" and r["value"] > 0]
    downrs = [r for r in rubrics if r["kind"] == "relative" and r["value"] < 0]

    # we now have a bracket [lo_score, hi_score]
    # e.g., suppose question out of 10 and two abs rubrics used
    # 3/4, 2/4 -> [5, 7]
    # Now relative "+1" rubrics modify the 5.  Relative "-1" rubrics
    # modify the 7.
    #
    # But you cannot lift the 5 above 7 nor drop the 7 below 5.

    # TODO: if bracket from abs is trivial, then further relatives are
    # modifiers.  In this case, we could decide mixing +/- is unambiguous.

    # step two: adjust with relative rubrics
    # uppers add to lower bound
    # downers subtract from the upper bound
    if uppers and downrs:
        # TODO: might relax above
        # e.g., if nontrivial bracket than its ambiguous to mix +/-
        raise PlomInconsistentRubricsException("Ambiguous to mix up and down deltas")

    if not absolutes and not uppers and not downrs:
        return None

    score = lo_score
    if uppers:
        score = lo_score + sum(r["value"] for r in uppers)
    if downrs:
        score = hi_score + sum(r["value"] for r in downrs)

    if score < 0 or score > maxscore:
        raise ValueError("score is out of range")

    if score < lo_score:
        raise ValueError("cannot drop score below that established by absolute rubrics")
    if score > hi_score:
        raise ValueError("cannot lift score above that established by absolute rubrics")

    return score


# compute_score = compute_score_naive
# compute_score = compute_score_legacy2022
compute_score = compute_score_locabs


def is_ambiguous(rubrics, maxscore):
    """TODO

    rough idea: returns false for mixed up/down?
    """
    pass
