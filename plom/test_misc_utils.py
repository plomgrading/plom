# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021, 2024 Colin B. Macdonald

from .misc_utils import format_int_list_with_runs
from .misc_utils import run_length_encoding
from .misc_utils import interpolate_questions_over_pages as interp


endash = "\N{EN DASH}"


def test_runs() -> None:
    L = ["1", "2", "3", "4", "7", "10", "11", "12", "13", "14", "64"]
    uout = f"1{endash}4, 7, 10{endash}14, 64"
    aout = "1-4, 7, 10-14, 64"
    assert format_int_list_with_runs(L, use_unicode=True) == uout
    assert format_int_list_with_runs(L, use_unicode=False) == aout
    assert format_int_list_with_runs(L) in (aout, uout)


def test_runs_zero_padding() -> None:
    L = ["1", "2", "3", "4", "7", "10", "11", "12", "13", "14", "64"]
    uout = f"0001{endash}0004, 0007, 0010{endash}0014, 0064"
    aout = "0001-0004, 0007, 0010-0014, 0064"
    assert format_int_list_with_runs(L, use_unicode=True, zero_padding=4) == uout
    assert format_int_list_with_runs(L, use_unicode=False, zero_padding=4) == aout


def test_runs_zero_padding2() -> None:
    L = ["7", "110", "111", "112", "113", "114"]
    aout = "07, 110-114"
    assert format_int_list_with_runs(L, use_unicode=False, zero_padding=2) == aout


def test_shortruns() -> None:
    L = ["1", "2", "4", "5", "6", "7", "9", "10", "12", "78", "79", "80"]
    out = "1, 2, 4-7, 9, 10, 12, 78-80"
    assert format_int_list_with_runs(L, use_unicode=False) == out


def test_runs_from_int_list() -> None:
    L = [1, 2, 3, 4, 20]
    out = "1-4, 20"
    assert format_int_list_with_runs(L, use_unicode=False) == out


def test_run_length_encoding() -> None:
    assert run_length_encoding([]) == []
    assert run_length_encoding([1]) == [(1, 0, 1)]
    assert run_length_encoding(["a"]) == [("a", 0, 1)]
    assert run_length_encoding(["a", 7, 7]) == [("a", 0, 1), (7, 1, 3)]
    assert run_length_encoding([None]) == [(None, 0, 1)]
    assert run_length_encoding([1, 1]) == [(1, 0, 2)]
    assert run_length_encoding([5, 5, 7]) == [(5, 0, 2), (7, 2, 3)]


def test_interp() -> None:
    assert interp(3, 3) == [[1], [2], [3]]


def test_interp_page_surplus() -> None:
    assert interp(3, 1) == [[1, 2, 3]]
    assert interp(4, 3) == [[1], [2], [3, 4]]
    assert interp(4, 2) == [[1, 2], [3, 4]]
    assert interp(5, 4) == [[1], [2], [3], [4, 5]]
    assert interp(5, 3) == [[1], [2], [3, 4, 5]]
    assert interp(5, 2) == [[1, 2], [3, 4, 5]]


def test_interp_shared_pages() -> None:
    assert interp(3, 4) == [[1], [1], [2], [3]]
    assert interp(3, 5) == [[1], [1], [2], [2], [3]]
    assert interp(3, 6) == [[1], [1], [2], [2], [3], [3]]
    assert interp(3, 7) == [[1], [1], [1], [2], [2], [3], [3]]


def test_interp_first_page() -> None:
    assert interp(3, 4, firstpg=0) == [[0], [0], [1], [2]]
    assert interp(3, 4, firstpg=5) == [[5], [5], [6], [7]]
    assert interp(3, 3, firstpg=2) == [[2], [3], [4]]
    assert interp(5, 2, firstpg=5) == [[5, 6], [7, 8, 9]]
