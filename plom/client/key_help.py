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
                "Box / Ellipse",
                ["c", ","],
                "Draw a highlight box (ellipse) on click (shift-click) and drag",
            ],
            [
                "Cross / QMark / Tick",
                ["e", "i"],
                "Draw a cross (question-mark / tick) on click (ctrl-click / shift-click) - note order.",
            ],
            [
                "Line / DoubleArrow / Arrow",
                ["b", "n"],
                "Draw a straight line (line-with-arrowheads / highlight) on click (ctrl-click / shift-click) and drag.",
            ],
            [
                "Pen / DoubleArrow / Highlighter",
                ["t", "y"],
                "Draw a free-hand line (line-with-arrowheads / highlight) on click (ctrl-click / shift-click).",
            ],
            [
                "Tick / QMark / Cross",
                ["d", "k"],
                "Draw a tick (question-mark / cross) on click (ctrl-click / shift-click) - note order.",
            ],
        ],
        "Delete": [
            [
                "Delete",
                ["x", "."],
                "Delete single item on click, or delete items in area on click and drag",
            ]
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
            ["Redo", ["w", "o", "ctrl-y"], "Redo the last undone-action."],
            ["Undo", ["s", "l", "ctrl-z"], "Undo the last action."],
        ],
        "Marks": [
            ["Delta=0", ["`"], "Set the delta-mark value to 0."],
            [
                "Delta=1",
                ["1"],
                "Set the delta-mark value to +1 (-1) when using mark-up (mark-down).",
            ],
            ["Delta=2", ["2"], "See delta=1"],
            ["Delta=3", ["3"], "See delta=1"],
            ["Delta=4", ["4"], "See delta=1"],
            ["Delta=5", ["5"], "See delta=1"],
            ["Delta=5", ["5"], "See delta=1"],
            ["Delta=6", ["6"], "See delta=1"],
            ["Delta=7", ["7"], "See delta=1"],
            ["Delta=8", ["8"], "See delta=1"],
            ["Delta=9", ["9"], "See delta=1"],
            ["Delta=10", ["0"], "See delta=1"],
        ],
        "Text": [
            [
                "Current comment",
                ["f", "j"],
                "Select the current comment from the comment list. A click then pastes the comment under the click. (Shift/right)-click-drag-click draws a highlight-box (until end of drag) and then a line connected to the comment (on final click).",
            ],
            [
                "End text edit",
                ["shift-enter", "shift-return"],
                'End the current text-edit and run latex if the text starts with "TEX:"',
            ],
            ["Escape text edit", ["esc"], "Escape from the current text edit."],
            [
                "Next comment",
                ["v", "m"],
                "Select the next comment from the comment list",
            ],
            [
                "Previous comment",
                ["r", "u"],
                "Select the previous comment from the comment list",
            ],
            [
                "Text",
                ["g", "h"],
                "Creates a text-item under the mouse click, or opens an existing text-item for editing. End the edit with shift-enter or escape.",
            ],
        ],
        "View": [
            ["Pan", ["q", "p"], "Click and drag moves the current view."],
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
                ["a", ";"],
                "Selects the zoom-tool. Zoom the view in (out) on click (shift-click).",
            ],
            ["Zoom-in", ["+", "="], "Zooms the view in."],
            ["Zoom-out", ["-", "_"], "Zooms the view out."],
        ],
    }

    def __init__(self, parent=None):
        super(KeyHelp, self).__init__()
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
        tw.setHorizontalHeaderLabels(["Function", "Keys", "Decription"])
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
