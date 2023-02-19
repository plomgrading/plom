# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020, 2023 Colin B. Macdonald

from PyQt5.QtCore import Qt
from plom.client.rubric_list import AddRubricBox


def test_AddRubricBox_add_new(qtbot):
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, [], None)
    qtbot.addWidget(d)
    assert d.windowTitle().startswith("Add")
    qtbot.mouseClick(d.TE, Qt.LeftButton)
    qtbot.keyClicks(d.TE, "new rubric")
    qtbot.mouseClick(d.typeRB_relative, Qt.LeftButton)
    # don't care what the default is but start at 2...
    d.relative_value_SB.setValue(2)
    # then decrement x3, should skip zero and give -2
    qtbot.keyClick(d.relative_value_SB, Qt.Key_Down)
    qtbot.keyClick(d.relative_value_SB, Qt.Key_Down)
    qtbot.keyClick(d.relative_value_SB, Qt.Key_Down)
    # path = qtbot.screenshot(d)
    # assert False, path
    d.accept()
    out = d.gimme_rubric_data()
    assert out["kind"] == "relative"
    assert out["display_delta"] == "-2"
    assert out["value"] == -2
    assert isinstance(out["value"], int)
    assert out["text"] == "new rubric"


def test_AddRubricBox_modify(qtbot):
    rub = {
        "id": 1234,
        "kind": "relative",
        "display_delta": "+1",
        "value": 1,
        "out_of": 0,
        "text": "some text",
        "tags": "",
        "meta": "",
        "username": "iser",
        "question": 1,
        "versions": [],
        "parameters": [],
    }
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, [], rub)
    qtbot.addWidget(d)
    assert d.windowTitle().startswith("Modify")
    assert not d.typeRB_neutral.isChecked()
    assert d.typeRB_relative.isChecked()

    # TODO: seems clicking doesn't work to set RadioButtons:
    qtbot.mouseClick(d.typeRB_neutral, Qt.LeftButton)
    qtbot.wait(10)
    qtbot.mouseClick(d.typeRB_neutral, Qt.LeftButton, delay=10)
    qtbot.wait(10)
    # times out after 5 seconds:
    # qtbot.waitUntil(lambda: d.typeRB_neutral.isChecked())
    # how to take a screenshot
    # path = qtbot.screenshot(d)
    # assert False, path
    # TODO: so instead we send it space bar
    qtbot.keyClicks(d.typeRB_neutral, " ")

    qtbot.mouseClick(d.TE, Qt.LeftButton)
    qtbot.keyClicks(d.TE, "-more")
    d.accept()
    out = d.gimme_rubric_data()
    assert out["kind"] == "neutral"
    assert out["display_delta"] == "."
    assert out["value"] == 0
    assert out["text"] == "some text-more"


def test_AddRubricBox_havest(qtbot):
    rub = {
        "id": 1234,
        "kind": "relative",
        "display_delta": "+1",
        "value": 1,
        "out_of": 0,
        "text": "will be replaced",
        "tags": "",
        "meta": "",
        "username": "user",
        "question": 1,
        "versions": [],
        "parameters": [],
    }
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, ["AAA", "BBB"], rub)
    qtbot.addWidget(d)
    qtbot.keyClicks(d.reapable_CB, "BBB")
    d.accept()
    out = d.gimme_rubric_data()
    assert out["text"] == "BBB"


def test_AddRubricBox_parameterize(qtbot):
    for v in (1, 2):
        d = AddRubricBox(None, "user", 10, 1, "Q1", v, 2, [], None, experimental=True)
        qtbot.addWidget(d)
        qtbot.mouseClick(d.TE, Qt.LeftButton)
        qtbot.keyClicks(d.TE, "tex: foo  $x$")
        # move back to the middle
        qtbot.keyClick(d.TE, Qt.Key_Left)
        qtbot.keyClick(d.TE, Qt.Key_Left)
        qtbot.keyClick(d.TE, Qt.Key_Left)
        qtbot.keyClick(d.TE, Qt.Key_Left)
        # insert param1 in the middle
        qtbot.mouseClick(d.scopeButton, Qt.LeftButton)
        qtbot.mouseClick(d.addParameterButton, Qt.LeftButton)
        qtbot.wait(10)
        # highlight the "x" text and replace it with param2
        qtbot.keyClick(d.TE, Qt.Key_End)
        qtbot.keyClick(d.TE, Qt.Key_Left)
        qtbot.keyClick(d.TE, Qt.Key_Left, modifier=Qt.ShiftModifier)
        qtbot.mouseClick(d.addParameterButton, Qt.LeftButton)
        qtbot.wait(10)
        # path = qtbot.screenshot(d)
        # assert False, path
        d.accept()
        out = d.gimme_rubric_data()
        assert out["text"] == "tex: foo <param1> $<param2>$"
        # the current version is replaced with the highlighted text
        exp = ['x', ''] if v == 1 else ['', 'x']
        assert out["parameters"] == [['<param1>', ['', '']], ['<param2>', exp]]
