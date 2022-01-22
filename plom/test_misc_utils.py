# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald

from .misc_utils import format_int_list_with_runs
from .misc_utils import run_length_encoding


def test_runs():
    L = ["1", "2", "3", "4", "7", "10", "11", "12", "13", "14", "64"]
    uout = "1–4, 7, 10–14, 64"
    aout = "1-4, 7, 10-14, 64"
    assert format_int_list_with_runs(L, use_unicode=True) == uout
    assert format_int_list_with_runs(L, use_unicode=False) == aout
    assert format_int_list_with_runs(L) in (aout, uout)


def test_shortruns():
    L = ["1", "2", "4", "5", "6", "7", "9", "10", "12", "78", "79", "80"]
    out = "1, 2, 4-7, 9, 10, 12, 78-80"
    assert format_int_list_with_runs(L, use_unicode=False) == out


def test_run_length_encoding():
    assert run_length_encoding([]) == []
    assert run_length_encoding([1]) == [(1, 0, 1)]
    assert run_length_encoding(["a"]) == [("a", 0, 1)]
    assert run_length_encoding([None]) == [(None, 0, 1)]
    assert run_length_encoding([1, 1]) == [(1, 0, 2)]
    assert run_length_encoding([5, 5, 7]) == [(5, 0, 2), (7, 2, 3)]
