# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from plom.tagging import is_valid_tag_text as valid


def test_tag_basic_valid(qtbot):
    assert valid("hello")
    assert valid("numb3rs")
    assert valid("under_score")
    assert valid("hy-phen")
    assert valid("me+you")
    assert valid(":colon:")
    assert valid("semicolon;")
    assert valid("@user1")


def test_tag_invalid_chars(qtbot):
    assert not valid("I <3 Plom")
    assert not valid("<blink>")


# less confident about these!  If the rules change, these could be adjusted
def test_tag_quiestionable(qtbot):
    assert not valid("two words")
    assert not valid("  stray_whitespace")
    assert not valid("stray_whitespace ")
