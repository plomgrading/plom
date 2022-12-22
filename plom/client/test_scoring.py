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


def test_legacy_score_sum_too_large_or_small():
    with raises(ValueError):
        lg([{"kind": "relative", "value": 2}, {"kind": "relative", "value": 4}], 5)
    with raises(ValueError):
        lg([{"kind": "relative", "value": -2}, {"kind": "relative", "value": -4}], 5)
