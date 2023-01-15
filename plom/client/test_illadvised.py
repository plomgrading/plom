# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from pytest import raises

from plom.client.rubrics import compute_score_locabs as score
from plom.client.rubrics import check_for_illadvised


def test_ill_no_warnings():
    maxscore = 10
    for rublist in (
        [],
        [
            {"kind": "absolute", "value": 10, "out_of": 10},
        ],
        [
            {"kind": "absolute", "value": 2, "out_of": 5},
            {"kind": "absolute", "value": 3, "out_of": 5},
        ],
    ):
        # any good situation here should not be an error from the scoring function
        score(rublist, maxscore)
        ok, code, msg = check_for_illadvised(rublist, maxscore)
        assert ok
        assert code is None
        assert msg is None


def test_ill_must_have_keys():
    with raises(KeyError, match="out_of"):
        check_for_illadvised([{"kind": "absolute", "value": 10}], 10)
    with raises(KeyError, match="kind"):
        check_for_illadvised([{"value": 10, "out_of": 10}], 10)
    with raises(KeyError, match="value"):
        check_for_illadvised([{"kind": "relative"}], 10)


def test_ill_not_enough_out_of():
    maxscore = 10
    rublist = [
        {"kind": "absolute", "value": 2, "out_of": 4},
        {"kind": "absolute", "value": 3, "out_of": 4},
    ]
    # example should be legal
    assert score(rublist, maxscore) <= maxscore
    ok, code, msg = check_for_illadvised(rublist, maxscore)
    assert not ok
    assert code
    assert code == "out-of-not-max-score"
    assert msg


def test_ill_too_much_out_of():
    maxscore = 10
    rublist = [
        {"kind": "absolute", "value": 2, "out_of": 4},
        {"kind": "absolute", "value": 3, "out_of": 4},
        {"kind": "absolute", "value": 4, "out_of": 4},
    ]
    # this one is also not legal, but seems like a good properly for illadvised too
    ok, code, msg = check_for_illadvised(rublist, maxscore)
    assert not ok
    assert code
    assert code == "out-of-not-max-score"
    assert msg


def test_ill_dont_mix_abs_minus_relative():
    maxscore = 10
    rublist = [
        {
            "kind": "absolute",
            "value": 2,
            "out_of": 4,
            "display_delta": "2 of 4",
            "text": "A",
        },
        {"kind": "relative", "value": -1, "display_delta": "-1", "text": "C"},
    ]
    # example should be legal
    assert score(rublist, maxscore) <= maxscore
    ok, code, msg = check_for_illadvised(rublist, maxscore)
    assert not ok
    assert code
    # note the rubrics out_of here is < maxscore but we nonetheless want a specific error
    assert code != "out-of-not-max-score"
    assert code == "dont-mix-abs-minus-relative"
    assert msg


def test_ill_dont_mix_abs_plus_relative():
    maxscore = 10
    rublist = [
        {
            "kind": "absolute",
            "value": 2,
            "out_of": 4,
            "display_delta": "2 of 4",
            "text": "A",
        },
        {"kind": "relative", "value": 1, "display_delta": "+1", "text": "C"},
    ]
    # example should be legal
    assert score(rublist, maxscore) <= maxscore
    ok, code, msg = check_for_illadvised(rublist, maxscore)
    assert not ok
    assert code
    # note the rubrics out_of here is < maxscore but we nonetheless want a specific error
    assert code != "out-of-not-max-score"
    assert code == "dont-mix-abs-plus-relative"
    assert msg
