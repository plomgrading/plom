# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

import re

import arrow

from plom.client.rubrics import diff_rubric, render_rubric_as_html


def _make_ex():
    return {
        "id": "123456123456",
        "username": "xenia",
        "kind": "absolute",
        "value": 2,
        "out_of": 4,
        "display_delta": "2 of 4",
        "text": "ABC",
    }


def test_basic_render() -> None:
    html = render_rubric_as_html(_make_ex())
    assert "ABC" in html


def test_rubric_diff() -> None:
    p = _make_ex()
    r = _make_ex()
    r.update({"text": "DEF"})
    same, diff = diff_rubric(p, p)
    assert same
    assert "no visible changes" in diff
    same, diff = diff_rubric(p, r)
    assert not same
    assert re.match(r"(?s).*\-.*ABC", diff)
    assert re.match(r"(?s).*\+.*DEF", diff)


def test_rubric_diff_delta() -> None:
    p = _make_ex()
    r = _make_ex()
    r.update({"value": 3, "display_delta": "3 of 4"})
    same, diff = diff_rubric(p, r)
    assert not same


def test_rubric_diff_version_change_issue3295() -> None:
    p = _make_ex()
    r = _make_ex()
    p.update({"versions": [1]})
    r.update({"versions": [1, 2]})
    same, diff = diff_rubric(p, r)
    assert not same
    assert "[1, 2]" in diff


def test_rubric_diff_tags() -> None:
    p = _make_ex()
    r = _make_ex()
    r.update({"tags": "foo"})
    same, diff = diff_rubric(p, r)
    assert not same
    assert "foo" in diff


def test_rubric_diff_when() -> None:
    p = _make_ex()
    r = _make_ex()
    r.update({"last_modified": arrow.now(), "text": "meh"})
    same, diff = diff_rubric(p, r)
    assert not same
    assert "just now" in diff
