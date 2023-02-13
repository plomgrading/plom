# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020, 2023 Colin B. Macdonald

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from plom.client.chooser import Chooser
from plom.client.useful_classes import BlankIDBox
from plom.client.rubric_list import AddRubricBox


def test_BlankIDBoxDialog(qtbot):
    d = BlankIDBox(None, 16)
    d.show()
    qtbot.addWidget(d)
    qtbot.mouseClick(d.noB, Qt.LeftButton)
    assert d.testNumber == 16


def test_BlankIDBoxDialog2(qtbot):
    d = BlankIDBox(None, 32)
    d.show()
    qtbot.addWidget(d)
    qtbot.mouseClick(d.blankB, Qt.LeftButton)
    assert d.testNumber == 32


def DISABLE_test_Chooser(qtbot):
    app = QApplication([])
    window = Chooser(app)
    window.show()
    qtbot.add_widget(window)
    # TODO: only if a local server is running, otherwise pops the dialog
    qtbot.mouseClick(window.ui.getServerInfoButton, Qt.LeftButton)
    assert window.ui.infoLabel.text().startswith("Server address")
    # TODO: seems to pop open the (model) dialog
    # qtbot.mouseClick(window.ui.optionsButton, Qt.LeftButton)
    # TODO: password too short, generates log should be so testable
    qtbot.mouseClick(window.ui.markButton, Qt.LeftButton)
    qtbot.mouseClick(window.ui.closeButton, Qt.LeftButton)


def DISABLE_test_Chooser_again(qtbot):
    # TODO: disabled as we cannot open another, maybe b/c this:
    # TODO: https://pytest-qt.readthedocs.io/en/3.3.0/app_exit.html
    app = QApplication([])
    window = Chooser(app)
    window.show()
    qtbot.addWidget(window)
    qtbot.mouseClick(window.ui.closeButton, Qt.LeftButton)


def test_AddRubricBox_add_new(qtbot):
    d = AddRubricBox(None, "user", 10, 1, "Q1", 1, 3, [], None)
    d.show()
    qtbot.addWidget(d)
    assert d.windowTitle().startswith("Add")
    qtbot.mouseClick(d.TE, Qt.LeftButton)
    qtbot.keyClicks(d.TE, "new rubric")
    qtbot.mouseClick(d.typeRB_relative, Qt.LeftButton)
    # path = qtbot.screenshot(d)
    # assert False, path
    d.accept()
    out = d.gimme_rubric_data()
    assert out["kind"] == "relative"
    assert out["display_delta"] == "+1"
    assert out["value"] == 1
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
