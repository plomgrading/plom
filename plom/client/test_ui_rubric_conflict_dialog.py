# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald

from __future__ import annotations

from pytest import raises

import arrow

from .rubric_conflict_dialog import RubricConflictDialog


def test_rubric_conflict_dialog_insufficient_args(qtbot) -> None:
    with raises(TypeError, match="missing"):
        RubricConflictDialog(None, "foo")  # type: ignore[call-arg]


def test_rubric_conflict_dialog(qtbot) -> None:
    rub0 = {
        "id": 1234,
        "display_delta": "+1",
        "text": "some text",
        "username": "admin",
    }
    rub1 = {
        "id": 1234,
        "display_delta": "+1",
        "text": "some new text",
        "username": "admin",
    }
    rub2 = {
        "id": 1234,
        "display_delta": "+2",
        "text": "some text",
        "username": "admin",
    }
    d = RubricConflictDialog(None, "foo error", rub1, rub2, rub0)
    qtbot.addWidget(d)
    assert "foo error" in d.text()
    d.accept()


def test_rubric_conflict_dialog_who_when(qtbot) -> None:
    rub0 = {
        "id": 1234,
        "display_delta": "+1",
        "text": "some text",
        "username": "admin",
    }
    rub1 = {
        "id": 1234,
        "display_delta": "+1",
        "text": "some new text",
        "username": "harry",
        "last_modified": arrow.now(),
    }
    rub2 = {
        "id": 1234,
        "display_delta": "+2",
        "text": "some text",
        "username": "sally",
        "last_modified": arrow.now(),
    }
    d = RubricConflictDialog(None, "foo", rub1, rub2, rub0)
    qtbot.addWidget(d)
    assert "harry" in d.text()
    assert "sally" in d.text()
    d.accept()
