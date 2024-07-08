# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Colin B. Macdonald

from PyQt6.QtCore import Qt
from plom.client.annotator import Annotator
from plom.client.marker import MarkerClient


class MockMarker:
    """Just enough Marker to open Annotator."""

    annotatorSettings = {
        "keybinding_name": None,
        "geometry": None,
        "zoomState": None,
        "compact": None,
        "keybinding_custom_overlay": None,
    }

    def getRubricsFromServer(self, q):
        return []

    def getTabStateFromServer(self):
        return []

    def is_experimental(self):
        return True

    def saveTabStateToServer(self, foo):
        pass


def test_annotr_open(qtbot):
    a = Annotator("some_user", MockMarker())
    a.show()
    qtbot.addWidget(a)
    # wait before closing: annotator has some buggy QTimer stuff...
    qtbot.wait(100)
    qtbot.wait(100)

    # mash some buttons
    for b in (
        a.boxButton,
        a.crossButton,
        a.deleteButton,
        a.lineButton,
        a.moveButton,
        a.panButton,
        a.penButton,
        a.textButton,
        a.tickButton,
        a.zoomButton,
    ):
        qtbot.mouseClick(b, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(a.undoButton, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(a.redoButton, Qt.MouseButton.LeftButton)

    # narrow mode, then reopen with UI button
    qtbot.keyClick(a, Qt.Key.Key_Home)
    qtbot.mouseClick(a.wideButton, Qt.MouseButton.LeftButton)
    qtbot.wait(10)
    # path = qtbot.screenshot(a)
    # assert False, path

    # clicking would do "next-paper": not prepared to test that yet
    # qtbot.mouseClick(a.finishedButton, Qt.MouseButton.LeftButton)
    qtbot.keyClick(a, Qt.Key.Key_C, modifier=Qt.KeyboardModifier.ControlModifier)


class MockQApp:
    downloader = None


def test_marker_open(qtbot):
    w = MarkerClient(MockQApp())
    # path = qtbot.screenshot(w)
    # assert False, path
    qtbot.mouseClick(w.closeButton, Qt.MouseButton.LeftButton)
