# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from plom.misc_utils import pprint_score as pp


def test_print_score_string() -> None:
    assert isinstance(pp(5), str)
    assert isinstance(pp(5.25), str)
    assert isinstance(pp(None), str)


def test_print_score_int_as_int() -> None:
    assert pp(5) == "5"


def test_print_score_no_trailing_zeros() -> None:
    assert not pp(5.25).endswith("0")
    assert not pp(5.5).startswith("5.50")


def test_print_score_none_as_blank() -> None:
    assert pp(None) == ""


def test_print_score_large_int() -> None:
    assert pp(1234567) == "1234567"
