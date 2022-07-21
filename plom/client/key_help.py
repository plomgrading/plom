# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

import importlib.resources as resources

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPainter, QPixmap, QMovie
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QGraphicsScene,
    QGraphicsView,
    QHeaderView,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

import plom.client.help_img


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
        # put rubric-nav and tool-nav into a tab
        self.tab.addTab(RubricNavPage(), "Rubric navigation")
        self.tab.addTab(ClickDragPage(), "Rubric click-drag-click")
        self.tab.addTab(ToolNavPage(), "Tool navigation")

        # Build a table for key lists
        tw = QTableWidget()
        tw.setColumnCount(3)
        tw.verticalHeader().hide()
        tw.setHorizontalHeaderLabels(["Function", "Keys", "Description"])
        tw.setAlternatingRowColors(True)
        tw.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tw.setSortingEnabled(True)

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


class RubricNavPage(QWidget):
    keys = {"rubric_prev": "e", "rubric_next": "d", "tab_prev": "s", "tab_next": "f"}

    def __init__(self):
        super().__init__()
        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform, True)

        self.scene = QGraphicsScene()
        self.put_stuff()
        self.view.setScene(self.scene)
        self.view.fitInView(
            self.scene.sceneRect().adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio
        )

        grid = QVBoxLayout()
        grid.addWidget(self.view)
        self.setLayout(grid)

    def put_stuff(self):
        pix = QPixmap()
        pix.loadFromData(resources.read_binary(plom.client.help_img, "nav_rubric.png"))
        self.scene.addPixmap(pix)  # is at position (0,0)

        sheet = "QPushButton { color : teal; font-size: 24pt;}"

        self.rn = QPushButton(self.keys["rubric_next"])
        self.rn.setStyleSheet(sheet)
        self.rn.setToolTip("Select next rubic")
        li = self.scene.addWidget(self.rn)
        li.setPos(330, 250)

        self.rp = QPushButton(self.keys["rubric_prev"])
        self.rp.setStyleSheet(sheet)
        self.rp.setToolTip("Select previous rubic")
        li = self.scene.addWidget(self.rp)
        li.setPos(330, 70)

        self.tp = QPushButton(self.keys["tab_prev"])
        self.tp.setStyleSheet(sheet)
        self.tp.setToolTip("Select previous tab of rubrics")
        li = self.scene.addWidget(self.tp)
        li.setPos(-40, -10)

        self.tn = QPushButton(self.keys["tab_next"])
        self.tn.setStyleSheet(sheet)
        self.tn.setToolTip("Select next tab of rubrics")
        li = self.scene.addWidget(self.tn)
        li.setPos(160, -10)


class ToolNavPage(QWidget):
    keys = {
        "tool_prev": "w",
        "tool_next": "r",
        "undo": "g",
        "redo": "t",
        "help": "?",
        "delete": "q",
        "zoom": "z",
    }

    def __init__(self):
        super().__init__()
        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform, True)

        self.scene = QGraphicsScene()
        self.put_stuff()
        self.view.setScene(self.scene)
        self.view.fitInView(
            self.scene.sceneRect().adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio
        )

        grid = QVBoxLayout()
        grid.addWidget(self.view)
        self.setLayout(grid)

    def put_stuff(self):
        pix = QPixmap()
        pix.loadFromData(resources.read_binary(plom.client.help_img, "nav_tools.png"))
        self.scene.addPixmap(pix)  # is at position (0,0)

        sheet = "QPushButton { color : teal; font-size: 24pt;}"

        self.tn = QPushButton(self.keys["tool_next"])
        self.tn.setStyleSheet(sheet)
        self.tn.setToolTip("Select next tool")
        li = self.scene.addWidget(self.tn)
        li.setPos(240, 300)

        self.tp = QPushButton(self.keys["tool_prev"])
        self.tp.setStyleSheet(sheet)
        self.tp.setToolTip("Select previous tool")
        li = self.scene.addWidget(self.tp)
        li.setPos(40, 300)

        self.ud = QPushButton(self.keys["undo"])
        self.ud.setStyleSheet(sheet)
        self.ud.setToolTip("Undo last action")
        li = self.scene.addWidget(self.ud)
        li.setPos(395, 155)

        self.rd = QPushButton(self.keys["redo"])
        self.rd.setStyleSheet(sheet)
        self.rd.setToolTip("Redo action")
        li = self.scene.addWidget(self.rd)
        li.setPos(395, 85)

        self.hlp = QPushButton(self.keys["help"])
        self.hlp.setStyleSheet(sheet)
        self.hlp.setToolTip("Pop up key help")
        li = self.scene.addWidget(self.hlp)
        li.setPos(350, -50)

        self.zm = QPushButton(self.keys["zoom"])
        self.zm.setStyleSheet(sheet)
        self.zm.setToolTip("Select zoom tool")
        li = self.scene.addWidget(self.zm)
        li.setPos(-40, -5)

        self.dlt = QPushButton(self.keys["delete"])
        self.dlt.setStyleSheet(sheet)
        self.dlt.setToolTip("Select delete tool")
        li = self.scene.addWidget(self.dlt)
        li.setPos(-40, 200)


class ClickDragPage(QWidget):
    def __init__(self):
        super().__init__()
        grid = QVBoxLayout()
        film_path = resources.path(plom.client.help_img, "click_drag.gif")
        film = QMovie(str(film_path))
        film_label = QLabel()
        film_label.setStyleSheet("QLabel {border-color: teal; border-style: outset; border-width: 2px;}" )
        film_label.setMovie(film)
        grid.addWidget(film_label)
        grid.addWidget(QLabel("Click-drag-release-move-click to highlight a region, and stamp rubric with a connecting line."))

        self.setLayout(grid)

        

        film.start()
