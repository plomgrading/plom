# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGridLayout,
    QHeaderView,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
)


class KeyHelp(QDialog):
    keyTypes = {
        "Annotation": [
            [
                "Next tool",
                ["r"],
                "Select the next tool",
            ],
            [
                "Previous tool",
                ["w"],
                "Select the previous tool",
            ],
            [
                "Select rubric / Next rubric",
                ["d"],
                "Selects the current rubric, or if rubric already selected, then moves to next rubric",
            ],
            [
                "Previous rubric",
                ["e"],
                "Select the previous rubric",
            ],
            [
                "Next tab",
                ["f"],
                "Select the next tab of rubrics",
            ],
            [
                "Previous tab",
                ["s"],
                "Select the previous tab of rubrics",
            ],
            ["Redo", ["t", "ctrl-y"], "Redo the last undone-action."],
            ["Undo", ["g", "ctrl-z"], "Undo the last action."],
            [
                "Delete",
                ["q"],
                "Delete single item on click, or delete items in area on click and drag",
            ],
            ["Move", ["a"], "Click and drag on an object to move it."],
        ],
        "Finishing": [
            [
                "Cancel",
                ["ctrl-c"],
                "Cancel the current annotations and return to the marker-window",
            ],
            [
                "Save and next",
                ["alt-enter", "alt-return", "ctrl-n", "ctrl-b"],
                "Save the current annotations and move on to next paper.",
            ],
        ],
        "General": [
            ["Show key help", ["?"], "Show this window."],
            ["Main menu", ["F10"], "Open the main menu"],
        ],
        "Text": [
            [
                "End text edit",
                ["shift-enter", "shift-return"],
                'End the current text-edit and run latex if the text starts with "TEX:"',
            ],
            ["Escape text edit", ["esc"], "Escape from the current text edit."],
        ],
        "View": [
            [
                "Pan-through",
                ["space"],
                "Moves through the current view, down and then right.",
            ],
            [
                "Pan-through (slowly)",
                ["ctrl-space"],
                "Moves slowly through the current view, down and then right.",
            ],
            [
                "Pan-back",
                ["shift-space"],
                "Moves back through the current view, up and then left.",
            ],
            [
                "Pan-back (slowly)",
                ["ctrl-shift-space"],
                "Moves slowly back through the current view, up and then left.",
            ],
            [
                "Show whole paper",
                ["F1", "Fn-F1"],
                "Opens a window to display all the pages of the current test being annotated (except the ID-page).",
            ],
            [
                "Toggle maximize window",
                ["\\"],
                "Toggles the window size to and from maximised.",
            ],
            [
                "Toggle wide-narrow",
                ["home"],
                "Toggles the tool-column between wide and narrow.",
            ],
            [
                "Toggle-zoom",
                ["ctrl-="],
                "Toggles between the user-set view, fit-height and fit-width.",
            ],
            [
                "Zoom",
                ["z"],
                "Selects the zoom-tool. Zoom the view in (out) on click (shift-click).",
            ],
            ["Zoom-in", ["+", "="], "Zooms the view in."],
            ["Zoom-out", ["-", "_"], "Zooms the view out."],
        ],
    }

    def __init__(self, parent=None):
        super().__init__()
        vb = QVBoxLayout()
        self.tab = QTabWidget()
        self.setTabs()
        self.cb = QPushButton("&close")
        self.cb.clicked.connect(self.accept)
        vb.addWidget(self.tab)
        vb.addWidget(self.cb)
        self.setLayout(vb)
        self.setMinimumSize(QSize(650, 400))

    def setTabs(self):
        # Now build one with everything together
        tw = QTableWidget()
        tw.setColumnCount(3)
        tw.verticalHeader().hide()
        tw.setHorizontalHeaderLabels(["Function", "Keys", "Description"])
        tw.setAlternatingRowColors(True)
        tw.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tw.setSortingEnabled(True)
        k = 0
        for div in self.keyTypes:
            for fun in self.keyTypes[div]:
                tw.insertRow(k)
                tw.setItem(k, 0, QTableWidgetItem(fun[0]))
                tw.setItem(
                    k,
                    1,
                    QTableWidgetItem(
                        ", ".join(list(map(lambda x: "{}".format(x), fun[1])))
                    ),
                )
                if len(fun) == 3:
                    tw.setItem(k, 2, QTableWidgetItem(fun[2]))
                k += 1
        tw.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tw.setWordWrap(True)
        # tw.resizeColumnsToContents()
        tw.resizeRowsToContents()
        self.tab.addTab(tw, "All")

        # build one for each division
        for div in self.keyTypes:
            tw = QTableWidget()
            tw.setColumnCount(3)
            tw.verticalHeader().hide()
            tw.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tw.setAlternatingRowColors(True)
            tw.setHorizontalHeaderLabels(["Function", "Keys", "Description"])
            tw.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tw.setSortingEnabled(True)
            k = 0
            for fun in self.keyTypes[div]:
                tw.insertRow(k)
                tw.setItem(k, 0, QTableWidgetItem(fun[0]))
                tw.setItem(
                    k,
                    1,
                    QTableWidgetItem(
                        ", ".join(list(map(lambda x: "{}".format(x), fun[1])))
                    ),
                )
                if len(fun) == 3:
                    tw.setItem(k, 2, QTableWidgetItem(fun[2]))
                k += 1
            # tw.resizeColumnsToContents()
            tw.resizeRowsToContents()
            self.tab.addTab(tw, div)
