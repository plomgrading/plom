# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from PyQt6.QtCore import Qt
from plom.client.annotator import Annotator


class MockMarker:
    """Just enough Marker to open Annotator"""

    annotatorSettings = {
        "keybinding_name": None,
        "geometry": None,
        "markWarnings": None,
        "rubricWarnings": None,
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
    # path = qtbot.screenshot(a)
    a.close()
    # clicking would do "next-paper": not prepared to test that yet
    # qtbot.mouseClick(a.finishedButton, Qt.MouseButton.LeftButton)
    qtbot.keyClick(a, Qt.Key.Key_C, modifier=Qt.KeyboardModifier.ControlModifier)
