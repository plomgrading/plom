# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021, 2023 Colin B. Macdonald

from pytest import raises

from plom.scan.question_list_utils import _parse_questions as parse
from plom.scan.question_list_utils import canonicalize_page_question_map as canonicalize
from plom.scan.question_list_utils import check_question_list as qlist


def test_all_to_empty():
    assert parse("all") == "all"
    assert parse("All") == "all"
    assert parse("ALL") == "all"


def test_list():
    assert parse("[1,2,  3]") == [1, 2, 3]


def test_list_of_lists():
    assert parse("[[1],[2,  3],  [4, 3,1]]") == [[1], [2, 3], [4, 3, 1]]
    assert parse("([1],[2,  3],  [4, 3,1])") == ([1], [2, 3], [4, 3, 1])


def test_scalar():
    assert parse("3") == 3


def test_implicit_list():
    assert parse("1,3,  2") == (1, 3, 2)
    assert parse("3,") == (3,)


def test_canonical_str_only_all():
    raises(ValueError, lambda: canonicalize("foo", 1, 1))
    assert isinstance(canonicalize("all", 2, 2), list)


def test_canonical_errors():
    raises(TypeError, lambda: canonicalize(5.6, 1, 1))
    raises(ValueError, lambda: canonicalize([1, 1.3], pages=1, numquestions=2))
    raises(ValueError, lambda: canonicalize([[1, 1.3]], pages=1, numquestions=2))


def test_canonical_error_not_enough_pages():
    raises(ValueError, lambda: canonicalize([[1], [1], [1]], pages=2, numquestions=1))


def test_canonical_error_not_enough_questions():
    raises(ValueError, lambda: canonicalize([[1, 2, 7]], pages=1, numquestions=2))


def test_canonical_error_mix_iter_noniter():
    raises(ValueError, lambda: canonicalize([[1], 2, [2]], pages=1, numquestions=2))


# TODO: we might replace these with dicts


def test_canonical_all_expansions():
    assert canonicalize("all", pages=2, numquestions=2) == [[1, 2], [1, 2]]
    assert canonicalize("all", pages=2, numquestions=3) == [[1, 2, 3], [1, 2, 3]]
    assert canonicalize("all", pages=1, numquestions=3) == [[1, 2, 3]]
    assert canonicalize("all", pages=3, numquestions=1) == [[1], [1], [1]]


def test_canonical_expansions():
    assert canonicalize(1, pages=2, numquestions=3) == [[1], [1]]
    assert canonicalize(2, pages=2, numquestions=3) == [[2], [2]]
    assert canonicalize([2, 3], pages=3, numquestions=3) == [[2, 3], [2, 3], [2, 3]]


def test_canonical_passthru():
    assert canonicalize([[1, 2], [2, 3]], pages=2, numquestions=3) == [[1, 2], [2, 3]]


def test_canonical_ranges():
    assert canonicalize([range(1, 3), range(2, 4)], pages=2, numquestions=3) == [
        [1, 2],
        [2, 3],
    ]


def test_canonical_tuples():
    assert canonicalize(((1,), (1, 2), [2, 3]), pages=3, numquestions=3) == [
        [1],
        [1, 2],
        [2, 3],
    ]


def test_qlist():
    assert qlist("all", 3) == [1, 2, 3]
    assert qlist("all", 2) == [1, 2]


def test_qlist_only_all():
    with raises(ValueError):
        qlist("ducks", 3)


def test_qlist_out_of_range():
    with raises(ValueError):
        qlist("[1, 10]", 3)
    with raises(ValueError):
        qlist("[-1, 2]", 3)


def test_qlist_not_int():
    with raises(ValueError):
        qlist("[1, 2.5]", 3)


def test__no_dupes():
    # Or decide its an error?
    # with raises(ValueError):
    #     qlist([2, 2, 2, 2, 1], 3)
    assert qlist([2, 2, 2, 2, 1], 3) == [1, 2]
    assert canonicalize([[1, 1], [2, 1, 2]], 2, 2) == [[1], [1, 2]]
