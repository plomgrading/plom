# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021, 2023-2024 Colin B. Macdonald

from pytest import raises

from plom.scan.question_list_utils import _parse_questions as parse
from plom.scan.question_list_utils import canonicalize_page_question_map as canonicalize
from plom.scan.question_list_utils import check_question_list as qlist


def test_all_to_empty() -> None:
    assert parse("all") == "all"
    assert parse("All") == "all"
    assert parse("ALL") == "all"


def test_list() -> None:
    assert parse("[1,2,  3]") == [1, 2, 3]


def test_list_of_lists() -> None:
    assert parse("[[1],[2,  3],  [4, 3,1]]") == [[1], [2, 3], [4, 3, 1]]
    assert parse("([1],[2,  3],  [4, 3,1])") == ([1], [2, 3], [4, 3, 1])


def test_scalar() -> None:
    assert parse("3") == 3


def test_implicit_list() -> None:
    assert parse("1,3,  2") == (1, 3, 2)
    assert parse("3,") == (3,)


def test_canonical_str_only_all() -> None:
    raises(ValueError, lambda: canonicalize("foo", 1, 1))
    assert isinstance(canonicalize("all", 2, 2), list)


def test_canonical_errors() -> None:
    raises(TypeError, lambda: canonicalize(5.6, 1, 1))
    raises(ValueError, lambda: canonicalize([1, 1.3], pages=1, numquestions=2))
    raises(ValueError, lambda: canonicalize([[1, 1.3]], pages=1, numquestions=2))


def test_canonical_error_not_enough_pages() -> None:
    raises(ValueError, lambda: canonicalize([[1], [1], [1]], pages=2, numquestions=1))


def test_canonical_error_not_enough_questions() -> None:
    raises(ValueError, lambda: canonicalize([[1, 2, 7]], pages=1, numquestions=2))


def test_canonical_error_mix_iter_noniter() -> None:
    raises(ValueError, lambda: canonicalize([[1], 2, [2]], pages=1, numquestions=2))


# TODO: we might replace these with dicts


def test_canonical_all_expansions() -> None:
    assert canonicalize("all", pages=2, numquestions=2) == [[1, 2], [1, 2]]
    assert canonicalize("all", pages=2, numquestions=3) == [[1, 2, 3], [1, 2, 3]]
    assert canonicalize("all", pages=1, numquestions=3) == [[1, 2, 3]]
    assert canonicalize("all", pages=3, numquestions=1) == [[1], [1], [1]]


def test_canonical_expansions() -> None:
    assert canonicalize(1, pages=2, numquestions=3) == [[1], [1]]
    assert canonicalize(2, pages=2, numquestions=3) == [[2], [2]]
    assert canonicalize([2, 3], pages=3, numquestions=3) == [[2, 3], [2, 3], [2, 3]]


def test_canonical_passthru() -> None:
    assert canonicalize([[1, 2], [2, 3]], pages=2, numquestions=3) == [[1, 2], [2, 3]]


def test_canonical_ranges() -> None:
    assert canonicalize([range(1, 3), range(2, 4)], pages=2, numquestions=3) == [
        [1, 2],
        [2, 3],
    ]


def test_canonical_tuples() -> None:
    assert canonicalize(((1,), (1, 2), [2, 3]), pages=3, numquestions=3) == [
        [1],
        [1, 2],
        [2, 3],
    ]


def test_qlist() -> None:
    assert qlist("all", 3) == [1, 2, 3]
    assert qlist("all", 2) == [1, 2]


def test_qlist_only_all() -> None:
    with raises(ValueError):
        qlist("ducks", 3)


def test_qlist_out_of_range() -> None:
    with raises(ValueError):
        qlist("[1, 10]", 3)
    with raises(ValueError):
        qlist("[-1, 2]", 3)


def test_qlist_not_int() -> None:
    with raises(ValueError):
        qlist("[1, 2.5]", 3)


def test__no_dupes() -> None:
    # Or decide its an error?
    # with raises(ValueError):
    #     qlist([2, 2, 2, 2, 1], 3)
    assert qlist([2, 2, 2, 2, 1], 3) == [1, 2]
    assert canonicalize([[1, 1], [2, 1, 2]], 2, 2) == [[1], [1, 2]]
