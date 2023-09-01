# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from typing import Any

from PyQt6.QtWidgets import (
    QPushButton,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QMenu,
    QRadioButton,
    QWidget,
    QWidgetAction,
)


def build_tagging_menu(parent: QWidget, get_paper_fcn) -> Any:
    """Build a pop-up menu/dialog thing for get-next preferences.

    Args:
        parent: the window that will popup this menu.
        get_paper_fcn: a function to call for the get particular
            paper number feature.

    Return:
        A QMenu with some monkey patched hackery: instance variables
        for manipulating the menu.  Probably it should be a subclass.
    """
    m = QMenu()
    # TODO: rather yuck
    m.addAction("Get paper number...", get_paper_fcn)
    m.addSection("Options")

    q = QComboBox()
    q.setEditable(True)
    m._prefer_tags_combobox = q
    a = QWidgetAction(parent)
    frame = QFrame()
    vlay = QVBoxLayout(frame)
    b = QRadioButton("Prefer tasks tagged for me")
    # TODO: would like on-by-default: Issue #2253
    # b.setChecked(True)
    m._prefer_tags_radiobuttons = [b]
    vlay.addWidget(b)
    b = QRadioButton("Prefer tasks tagged")
    m._prefer_tags_radiobuttons.append(b)
    lay = QHBoxLayout()
    lay.addWidget(b)
    lay.addWidget(q)
    vlay.addLayout(lay)
    b = QRadioButton("No preference for tagged papers")
    b.setChecked(True)
    m._prefer_tags_radiobuttons.append(b)
    vlay.addWidget(b)
    a.setDefaultWidget(frame)
    m.addAction(a)

    a = QWidgetAction(parent)
    frame = QFrame()
    lay = QHBoxLayout(frame)
    q = QCheckBox("Prefer paper number \N{Greater-than Or Equal To}")
    q.setCheckable(True)
    q.setChecked(False)
    lay.addWidget(q)
    t = QLineEdit()
    t.setText("0")
    lay.addWidget(t)
    a._lineedit = t
    a._checkbox = q
    a.setDefaultWidget(frame)
    m._prefer_above_action = a
    m.addAction(a)

    a = QWidgetAction(parent)
    frame = QFrame()
    lay = QHBoxLayout(frame)
    lay.addStretch()
    b = QPushButton("Ok")
    b.clicked.connect(m.close)
    lay.addWidget(b)
    a.setDefaultWidget(frame)
    m.addAction(a)

    return m
