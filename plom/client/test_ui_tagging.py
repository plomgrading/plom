# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox
from plom.client.useful_classes import AddRemoveTagDialog


def test_tag_add(qtbot):
    d = AddRemoveTagDialog(None, [], [])
    d.show()
    qtbot.addWidget(d)
    qtbot.keyClicks(d.CBadd, "tag!")
    d.add_tag()
    assert d.return_values == ("add", "tag!")


def test_tag_cancel_dialog(qtbot):
    d = AddRemoveTagDialog(None, [], [])
    d.show()
    qtbot.addWidget(d)
    qtbot.keyClick(d, Qt.Key.Key_Escape)
    assert d.return_values is None
    assert not d.isVisible()


def test_tag_choices_but_still_freeform(qtbot):
    d = AddRemoveTagDialog(None, [], ["old"])
    d.show()
    qtbot.addWidget(d)
    qtbot.keyClicks(d.CBadd, "tag!")
    d.add_tag()
    assert d.return_values == ("add", "tag!")


def test_tag_choices(qtbot):
    d = AddRemoveTagDialog(None, [], ["me", "too"])
    d.show()
    qtbot.addWidget(d)
    qtbot.keyClicks(d.CBadd, "me")
    d.add_tag()
    assert d.return_values == ("add", "me")


def test_tag_remove(qtbot, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes
    )
    d = AddRemoveTagDialog(None, ["tag1", "tag2", "tag3"], [])
    d.show()
    qtbot.addWidget(d)
    d.remove_tag("tag2")
    assert d.return_values == ("remove", "tag2")
    assert not d.isVisible()