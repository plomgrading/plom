# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
import sys
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

stringOfLegalKeys = "qwertyuiop[]asdfghjkl;'zxcvbnm,./"

the_actions = [
    "nextRubric",
    "previousRubric",
    "nextPane",
    "previousPane",
    "nextTool",
    "previousTool",
    "undo",
    "redo",
]

keys_sdf = {
    "redo": "T",
    "undo": "G",
    "nextRubric": "E",
    "previousRubric": "D",
    "nextPane": "F",
    "previousPane": "S",
    "nextTool": "R",
    "previousTool": "W",
}

keys_fr = {
    "redo": "T",
    "undo": "G",
    "nextRubric": "F",
    "previousRubric": "R",
    "nextPane": "D",
    "previousPane": "S",
    "nextTool": "E",
    "previousTool": "W",
}


class SingleKeyEdit(QLineEdit):
    def __init__(self, parent, currentKey=None, legal=None):
        super(SingleKeyEdit, self).__init__()
        self.parent = parent
        self.setAlignment(Qt.AlignHCenter)
        self.legal = legal
        if currentKey:
            self.theKey = currentKey
            self.theCode = QKeySequence(self.theKey)[0]
            self.setText(currentKey)
        else:
            self.theKey = ""

    def keyPressEvent(self, event):
        keyCode = event.key()
        # no modifiers please
        if keyCode in [Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta]:
            return
        if keyCode in [Qt.Key_Backspace, Qt.Key_Delete]:
            self.backspace()
            self.theCode = None
            self.theKey = ""
            return
        if keyCode not in self.legal:
            return
        self.theCode = keyCode

    def keyReleaseEvent(self, event):
        self.theKey = QKeySequence(self.theCode).toString()
        self.setText(self.theKey)


class KeyWrangler(QWidget):
    def __init__(self, currentKeys=None):
        super(KeyWrangler, self).__init__()
        if currentKeys is None:
            currentKeys = keys_sdf
        self.currentKeys = currentKeys
        self.legalKeyCodes = [QKeySequence(c)[0] for c in stringOfLegalKeys]
        self.actions = the_actions

        for act in self.actions:
            setattr(self, act + "Label", QLabel(act))
            setattr(
                self,
                act + "KeyInput",
                SingleKeyEdit(self, self.currentKeys[act], legal=self.legalKeyCodes),
            )

        self.sdfB = QPushButton("Set SDF")
        self.sdfB.clicked.connect(self.setSDF)
        self.frB = QPushButton("Set FR")
        self.frB.clicked.connect(self.setFR)
        self.vB = QPushButton("Validate")
        self.vB.clicked.connect(self.validate)

        grid = QGridLayout()
        for r, act in enumerate(self.actions):
            grid.addWidget(getattr(self, act + "Label"), r, 1)
            grid.addWidget(getattr(self, act + "KeyInput"), r, 2)
        grid.addWidget(self.sdfB, 0, 3)
        grid.addWidget(self.frB, 0, 4)
        grid.addWidget(self.vB, 4, 3)
        self.setLayout(grid)

    def setSDF(self):
        for act in self.actions:
            getattr(self, act + "KeyInput").setText(keys_sdf[act])

    def setFR(self):
        for act in self.actions:
            getattr(self, act + "KeyInput").setText(keys_fr[act])

    def validate(self):
        actToCode = {}
        for act in self.actions:
            actToCode[act] = getattr(self, act + "KeyInput").theCode
            if actToCode[act] is None:
                print("Is invalid - '{}' is missing a key".format(act))
                return False
        # check for duplications
        for n, act in enumerate(self.actions):
            for k in range(0, n):
                if actToCode[act] == actToCode[self.actions[k]]:
                    print(
                        "Is invalid '{}' and '{}' have same key '{}'".format(
                            act, self.actions[k], QKeySequence(actToCode[act])[0]
                        )
                    )
                    return False
        return True


def main(args):
    app = QApplication(args)
    kw = KeyWrangler()
    kw.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main([""])
