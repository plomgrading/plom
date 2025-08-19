# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2025 Andrew Rechnitzer

from __future__ import annotations

import math
from math import isclose
from typing import Any

from pytest import raises

from plom.rubric_utils import compute_score_legacy2022 as lg
from plom.rubric_utils import compute_score_locabs as s
from plom.rubric_utils import compute_score_naive as naive
from plom.plom_exceptions import PlomInconsistentRubric, PlomInvalidRubric


def test_naive_score() -> None:
    r = [
        {"kind": "absolute", "value": 10},
        {"kind": "relative", "value": -2},
        {"kind": "relative", "value": 1},
        {"kind": "neutral", "value": 0},
    ]
    assert naive(r, 10) == 9


def test_naive_legacy_out_of_range() -> None:
    r = [
        {"kind": "relative", "value": 4},
        {"kind": "relative", "value": 3},
    ]
    with raises(ValueError, match="out of range"):
        naive(r, 5)
    with raises(ValueError, match="out of range"):
        lg(r, 5)


def test_legacy_score() -> None:
    r = [{"kind": "absolute", "value": 10}]
    assert lg(r, 10) == 10


def test_legacy_accepts_string_values() -> None:
    # not sure if future will but legacy should
    assert lg([{"kind": "absolute", "value": "5"}], 5) == 5
    assert lg([{"kind": "relative", "value": "+1"}], 5) == 1
    assert lg([{"kind": "relative", "value": "-1"}], 5) == 4


def test_legacy_none() -> None:
    assert lg([], 10) is None
    assert lg([{"kind": "neutral"}], 10) is None
    assert lg([{"kind": "neutral", "value": 0}], 10) is None


def test_legacy_score_out_range() -> None:
    with raises(ValueError):
        lg([{"kind": "absolute", "value": -1}], 5)
    with raises(ValueError):
        lg([{"kind": "absolute", "value": 6}], 5)


def test_legacy_score_no_partial_absolute_rubrics() -> None:
    with raises(ValueError):
        lg([{"kind": "absolute", "value": 10}], 12)


def test_legacy_score_only_one_absolute_rubric() -> None:
    with raises(PlomInconsistentRubric):
        lg([{"kind": "absolute", "value": 0}, {"kind": "absolute", "value": 0}], 5)


def test_legacy_score_no_mix_relative_absolute_rubric() -> None:
    with raises(PlomInconsistentRubric):
        lg([{"kind": "absolute", "value": 0}, {"kind": "relative", "value": -1}], 5)


def test_legacy_score_no_mix_up_down_rubrics() -> None:
    with raises(PlomInconsistentRubric):
        lg([{"kind": "relative", "value": 2}, {"kind": "relative", "value": -1}], 5)


def test_legacy_score_relative() -> None:
    assert lg([{"kind": "relative", "value": -1}], 5) == 4
    assert lg([{"kind": "relative", "value": 1}], 5) == 1
    assert (
        lg([{"kind": "relative", "value": 2}, {"kind": "relative", "value": 3}], 5) == 5
    )
    assert (
        lg([{"kind": "relative", "value": -1}, {"kind": "relative", "value": -2}], 5)
        == 2
    )


def test_score_sum_too_large_or_small() -> None:
    with raises(ValueError):
        s([{"kind": "relative", "value": 2}, {"kind": "relative", "value": 4}], 5)
    with raises(ValueError):
        s([{"kind": "relative", "value": -2}, {"kind": "relative", "value": -4}], 5)


def test_score_out_range() -> None:
    with raises(ValueError):
        s([{"kind": "absolute", "value": -1, "out_of": 5}], 5)
    with raises(ValueError):
        s([{"kind": "absolute", "value": 6, "out_of": 5}], 5)


def test_int_score_multiple_absolute_rubric() -> None:
    def mk_rubrics(a, b, c, d):
        return [
            {"kind": "absolute", "value": a, "out_of": b},
            {"kind": "absolute", "value": c, "out_of": d},
        ]

    assert s(mk_rubrics(0, 2, 0, 3), 5) == 0
    assert s(mk_rubrics(2, 2, 3, 3), 5) == 5
    assert s(mk_rubrics(2, 2, 0, 3), 5) == 2
    assert s(mk_rubrics(1, 2, 2, 3), 5) == 3
    with raises(ValueError, match="outside"):
        s(mk_rubrics(1, 2, -1, 3), 5)
    with raises(ValueError, match="outside"):
        s(mk_rubrics(1, 2, 4, 3), 5)
    with raises(ValueError, match="outside"):
        s(mk_rubrics(1, 2, 1, 0), 5)
    with raises(ValueError, match="outside"):
        s(mk_rubrics(1, 2, 1, 6), 5)
    with raises(ValueError, match="outside"):
        s(mk_rubrics(1, 4, 1, 4), 5)


def test_float_score_multiple_absolute_rubric() -> None:
    def mk_rubrics(a, b, c, d):
        return [
            {"kind": "absolute", "value": a, "out_of": b},
            {"kind": "absolute", "value": c, "out_of": d},
        ]

    assert s(mk_rubrics(0.5, 2.0, 0.5, 3.0), 5) == 1.0
    assert s(mk_rubrics(0.0, 2.0, 0.0, 3.0), 5) == 0.0
    assert s(mk_rubrics(2.0, 2.0, 3.0, 3.0), 5) == 5.0

    # hard numbers get a tolerance of 1e-9
    X = s(mk_rubrics(2.0, 2.0, 0.1, 3.0), 5)
    Y = 2.1
    assert X is not None
    assert isclose(X, Y)
    X = s(mk_rubrics(1 / 3, 2.0, 2 / 5, 3.0), 5)
    Y = 11 / 15
    assert X is not None
    assert isclose(X, Y)
    X = s(mk_rubrics(1 / 3, 2.0, 0.5, 3.0), 5)
    Y = 5 / 6
    assert X is not None
    assert isclose(X, Y)

    # check non-representable `out_of`s don't raise warnings
    s([{"kind": "absolute", "value": 0.0, "out_of": 1 / 3} for i in range(3)], 1)
    s([{"kind": "absolute", "value": 0.0, "out_of": 5 / 6} for i in range(6)], 5)

    with raises(ValueError, match="outside"):
        s(mk_rubrics(1.0, 2.0, -1.0, 3.0), 5)
    with raises(ValueError, match="outside"):
        s(mk_rubrics(1.0, 2.0, 4.0, 3.0), 5)
    with raises(ValueError, match="outside"):
        s(mk_rubrics(7 / 3, 2.0, 2.0, 2.0), 5)
    with raises(ValueError, match="outside"):
        s(mk_rubrics(1.0, 2.0, 1.0, 0.0), 5)


def test_int_score_mix_absolute_rubric_with_relative() -> None:
    def mk_rubrics(a, b, c):
        return [
            {"kind": "absolute", "value": a, "out_of": b},
            {"kind": "relative", "value": c},
        ]

    assert s(mk_rubrics(0, 2, 1), 5) == 1
    assert s(mk_rubrics(0, 2, 2), 5) == 2
    assert s(mk_rubrics(0, 2, 3), 5) == 3
    # maybe people want to use them in this way...?
    with raises(ValueError, match="above.*absolute"):
        s(mk_rubrics(0, 2, 4), 5)
    # assert s(mk_rubrics(3, 5, 1), 5) == 4  # should not be err once trivial bracket?

    assert s(mk_rubrics(1, 2, 1), 5) == 2
    assert s(mk_rubrics(1, 2, 2), 5) == 3
    assert s(mk_rubrics(1, 2, 3), 5) == 4
    with raises(ValueError, match="above.*absolute"):
        s(mk_rubrics(1, 2, 4), 5)

    assert s(mk_rubrics(2, 2, 1), 5) == 3
    assert s(mk_rubrics(2, 2, 2), 5) == 4
    assert s(mk_rubrics(2, 2, 3), 5) == 5
    with raises(ValueError, match="out of range"):
        s(mk_rubrics(2, 2, 4), 5)

    assert s(mk_rubrics(0, 2, -1), 5) == 2
    assert s(mk_rubrics(0, 2, -2), 5) == 1
    assert s(mk_rubrics(0, 2, -3), 5) == 0
    with raises(ValueError, match="out of range"):
        s(mk_rubrics(0, 2, -4), 5)

    assert s(mk_rubrics(0, 3, -1), 5) == 1
    assert s(mk_rubrics(0, 3, -2), 5) == 0
    with raises(ValueError, match="out of range"):
        s(mk_rubrics(0, 3, -3), 5)

    assert s(mk_rubrics(2, 3, -1), 5) == 3
    assert s(mk_rubrics(2, 3, -2), 5) == 2
    with raises(ValueError, match="below.*absolute"):
        s(mk_rubrics(2, 3, -3), 5)
    with raises(ValueError, match="below.*absolute"):
        s(mk_rubrics(2, 3, -4), 5)
    with raises(ValueError, match="out of range"):
        s(mk_rubrics(2, 3, -5), 5)


def test_float_score_mix_absolute_rubric_with_relative() -> None:
    def mk_rubrics(a, b, c):
        return [
            {"kind": "absolute", "value": a, "out_of": b},
            {"kind": "relative", "value": c},
        ]

    assert s(mk_rubrics(0.0, 2.0, 0.5), 5) == 0.5
    assert s(mk_rubrics(0.0, 2.0, 3.0), 5) == 3.0
    with raises(ValueError, match="above.*absolute"):
        s(mk_rubrics(0.0, 2.0, 4.0), 5)

    assert s(mk_rubrics(1.0, 2.0, 0.5), 5) == 1.5
    assert s(mk_rubrics(1.0, 2.0, 3.0), 5) == 4.0
    with raises(ValueError, match="above.*absolute"):
        s(mk_rubrics(1.0, 2, 3.1), 5)

    assert s(mk_rubrics(2.0, 2.0, 0.5), 5) == 2.5
    assert s(mk_rubrics(2.0, 2.0, 3.0), 5) == 5.0
    with raises(ValueError, match="out of range"):
        s(mk_rubrics(2.0, 2.0, 3.5), 5)

    assert s(mk_rubrics(0.0, 2.0, -0.5), 5) == 2.5
    assert s(mk_rubrics(0.0, 2.0, -3.0), 5) == 0.0
    with raises(ValueError, match="out of range"):
        s(mk_rubrics(0.0, 2.0, -4.0), 5)

    assert s(mk_rubrics(2.0, 2.0, -2.0), 5) == 3.0
    assert s(mk_rubrics(2.0, 2.0, -3.0), 5) == 2.0
    with raises(ValueError, match="below.*absolute"):
        s(mk_rubrics(2.0, 2.0, -3.5), 5)
    with raises(ValueError, match="out of range"):
        s(mk_rubrics(2.0, 3.0, -5.0), 5)

    # recurring+irrational numbers
    assert s(mk_rubrics(0.0, 2.0, 1 / 3), 5) == 1 / 3
    assert s(mk_rubrics(2.0, 2.0, 1 / 3), 5) == 7 / 3
    assert s(mk_rubrics(1 / 3, 2.0, math.exp(1)), 5) == 1 / 3 + math.exp(1)


def test_score_return_type() -> None:
    def mk_rubrics(kind1, value1, out_of1, kind2, value2, out_of2):
        return [
            {"kind": kind1, "value": value1, "out_of": out_of1},
            {"kind": kind2, "value": value2, "out_of": out_of2},
        ]

    score = s(mk_rubrics("absolute", 2.0, 3.0, "absolute", 2.0, 2.0), 5)
    assert type(score) is float
    score = s(mk_rubrics("absolute", 2.0, 3.0, "relative", 2.0, 0.0), 5)
    assert type(score) is float
    score = s(mk_rubrics("absolute", 2.0, 3.0, "relative", -2.0, 0.0), 5)
    assert type(score) is float
    score = s(mk_rubrics("relative", 2.0, 3.0, "relative", 2.0, 2.0), 5)
    assert type(score) is float
    score = s(mk_rubrics("absolute", 2.0, 3.0, "neutral", 2.0, 0.0), 5)
    assert type(score) is float
    score = s(mk_rubrics("relative", 2.0, 3.0, "neutral", 2.0, 2.0), 5)
    assert type(score) is float

    score = s(mk_rubrics("absolute", 2, 3, "absolute", 2, 2), 5)
    assert type(score) is int
    score = s(mk_rubrics("absolute", 2, 3, "relative", 2, 0), 5)
    assert type(score) is int
    score = s(mk_rubrics("absolute", 2, 3, "relative", -2, 0), 5)
    assert type(score) is int
    score = s(mk_rubrics("relative", 2, 3, "relative", 2, 2), 5)
    assert type(score) is int
    score = s(mk_rubrics("absolute", 2, 3, "neutral", 2, 0), 5)
    assert type(score) is int
    score = s(mk_rubrics("relative", 2, 3, "neutral", 2, 2), 5)
    assert type(score) is int


def test_score_none() -> None:
    assert s([], 10) is None
    assert s([{"kind": "neutral"}], 10) is None
    assert s([{"kind": "neutral", "value": 0}], 10) is None


def test_score_ambiguous_mix_up_down() -> None:
    r = [
        {"kind": "relative", "value": 4},
        {"kind": "relative", "value": -3},
    ]
    with raises(PlomInconsistentRubric, match="Ambiguous"):
        s(r, 10)


def test_score_invalid_kind() -> None:
    with raises(PlomInvalidRubric, match="kind"):
        lg([{"kind": "sHiFtY"}], 5)
    with raises(PlomInvalidRubric, match="kind"):
        s([{"kind": "sHiFtY"}], 5)


def test_score_exclusive() -> None:
    # TODO: group storage still in-flux: adjust test if it moves out of tags
    r = [
        {"kind": "absolute", "value": 2, "out_of": 5, "tags": "exclusive:foo"},
        {"kind": "absolute", "value": 1, "out_of": 5, "tags": "exclusive:foo"},
    ]
    with raises(ValueError, match="exclusive.*foo"):
        s(r, 10)


def test_score_exclusive_not_only_absolute() -> None:
    # TODO: group storage still in-flux: adjust test if it moves out of tags
    r: list[dict[str, Any]] = [
        {"kind": "neutral", "tags": "exclusive:bar"},
        {"kind": "relative", "value": -1, "tags": "exclusive:bar"},
    ]
    with raises(ValueError, match="exclusive.*bar"):
        s(r, 10)


def test_score_exclusive_diff_groups_ok() -> None:
    # TODO: group storage still in-flux: adjust test if it moves out of tags
    r: list[dict[str, Any]] = [
        {"kind": "neutral", "tags": "exclusive:foo"},
        {"kind": "neutral", "tags": "exclusive:baz"},
    ]
    s(r, 10)  # no ValueError
