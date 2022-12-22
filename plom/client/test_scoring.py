# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Colin B. Macdonald

from copy import deepcopy
from pathlib import Path
import sys

from pytest import raises

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from plom.plom_exceptions import PlomInconsistentRubricsException
from plom.client.rubrics import compute_score_naive as naive
from plom.client.rubrics import compute_score_legacy2022 as lg
from plom.client.rubrics import compute_score_locabs as s


def test_naive_score():
    r = [
        {"kind": "absolute", "value": 10},
        {"kind": "relative", "value": -2},
        {"kind": "relative", "value": 1},
        {"kind": "neutral", "value": 0},
    ]
    assert naive(r, 10) == 9


def test_legacy_score():
    r = [{"kind": "absolute", "value": 10}]
    assert lg(r, 10) == 10


def test_legacy_accepts_string_values():
    # not sure if future will but legacy should
    assert lg([{"kind": "absolute", "value": "5"}], 5) == 5
    assert lg([{"kind": "relative", "value": "+1"}], 5) == 1
    assert lg([{"kind": "relative", "value": "-1"}], 5) == 4


def test_legacy_score_out_range():
    with raises(ValueError):
        lg([{"kind": "absolute", "value": -1}], 5)
    with raises(ValueError):
        lg([{"kind": "absolute", "value": 6}], 5)


def test_legacy_score_no_partial_absolute_rubrics():
    with raises(ValueError):
        lg([{"kind": "absolute", "value": 10}], 12)


def test_legacy_score_only_one_absolute_rubric():
    with raises(PlomInconsistentRubricsException):
        lg([{"kind": "absolute", "value": 0}, {"kind": "absolute", "value": 0}], 5)


def test_legacy_score_no_mix_relative_absolute_rubric():
    with raises(PlomInconsistentRubricsException):
        lg([{"kind": "absolute", "value": 0}, {"kind": "relative", "value": -1}], 5)


def test_legacy_score_no_mix_up_down_rubrics():
    with raises(PlomInconsistentRubricsException):
        lg([{"kind": "relative", "value": 2}, {"kind": "relative", "value": -1}], 5)


def test_legacy_score_relative():
    assert lg([{"kind": "relative", "value": -1}], 5) == 4
    assert lg([{"kind": "relative", "value": 1}], 5) == 1
    assert (
        lg([{"kind": "relative", "value": 2}, {"kind": "relative", "value": 3}], 5) == 5
    )
    assert (
        lg([{"kind": "relative", "value": -1}, {"kind": "relative", "value": -2}], 5)
        == 2
    )


def test_score_sum_too_large_or_small():
    with raises(ValueError):
        s([{"kind": "relative", "value": 2}, {"kind": "relative", "value": 4}], 5)
    with raises(ValueError):
        s([{"kind": "relative", "value": -2}, {"kind": "relative", "value": -4}], 5)


def test_score_out_range():
    with raises(ValueError):
        s([{"kind": "absolute", "value": -1, "out_of": 5}], 5)
    with raises(ValueError):
        s([{"kind": "absolute", "value": 6, "out_of": 5}], 5)


def test_score_multiple_absolute_rubric():
    def mk_rubrics(a, b, c, d):
        return [
            {"kind": "absolute", "value": a, "out_of": b},
            {"kind": "absolute", "value": c, "out_of": d},
        ]

    assert s(mk_rubrics(0, 2, 0, 3), 5) == 0
    assert s(mk_rubrics(2, 2, 3, 3), 5) == 5
    assert s(mk_rubrics(2, 2, 0, 3), 5) == 2
    assert s(mk_rubrics(1, 2, 2, 3), 5) == 3
    # fmt: off
    with raises(ValueError, match="outside"): s(mk_rubrics(1, 2, -1, 3), 5)
    with raises(ValueError, match="outside"): s(mk_rubrics(1, 2, 4, 3), 5)
    with raises(ValueError, match="outside"): s(mk_rubrics(1, 2, 1, 0), 5)
    with raises(ValueError, match="outside"): s(mk_rubrics(1, 2, 1, 6), 5)
    with raises(ValueError, match="outside"): s(mk_rubrics(1, 4, 1, 4), 5)
    # fmt: on


def test_score_mix_absolute_rubric_with_relative():
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
