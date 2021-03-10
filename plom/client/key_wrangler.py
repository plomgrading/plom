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
from .useful_classes import ErrorMessage

stringOfLegalKeys = "qwertyuiop[]asdfghjkl;'zxcvbnm,./"

the_actions = [
    "previousRubric",
    "nextRubric",
    "previousPane",
    "nextPane",
    "previousTool",
    "nextTool",
    "redo",
    "undo",
    "delete",
    "move",
    "zoom",
]

keys_sdf = {
    "redo": "T",
    "undo": "G",
    "nextRubric": "D",
    "previousRubric": "E",
    "nextPane": "F",
    "previousPane": "S",
    "nextTool": "R",
    "previousTool": "W",
    "delete": "Q",
    "move": "A",
    "zoom": "Z",
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
    "delete": "Q",
    "move": "A",
    "zoom": "Z",
}

keys_asd = {
    "redo": "R",
    "undo": "F",
    "nextRubric": "S",
    "previousRubric": "W",
    "nextPane": "D",
    "previousPane": "A",
    "nextTool": "E",
    "previousTool": "Q",
    "delete": "C",
    "move": "X",
    "zoom": "Z",
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

    def setText(self, omega):
        self.theKey = omega
        if len(omega) > 0:
            self.theCode = QKeySequence(omega)[0]
        super().setText(omega)


class KeyWrangler(QDialog):
    def __init__(self, currentKeys=None):
        super(KeyWrangler, self).__init__()
        if currentKeys is None:
            currentKeys = keys_sdf
        self.currentKeys = currentKeys
        self.legalKeyCodes = [QKeySequence(c)[0] for c in stringOfLegalKeys]
        self.actions = the_actions

        for act in self.actions:
            setattr(self, act + "Label", QLabel(act))
            getattr(self, act + "Label").setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            setattr(
                self,
                act + "Key",
                SingleKeyEdit(self, self.currentKeys[act], legal=self.legalKeyCodes),
            )

        self.sdfB = QPushButton("Set SDF")
        self.sdfB.clicked.connect(self.setSDF)
        self.asdB = QPushButton("Set ASD")
        self.asdB.clicked.connect(self.setASD)
        self.frB = QPushButton("Set FR")
        self.frB.clicked.connect(self.setFR)
        self.vB = QPushButton("Validate")
        self.vB.clicked.connect(self.validate)
        self.aB = QPushButton("Accept layout")
        self.aB.clicked.connect(self.acceptLayout)
        self.cB = QPushButton("Reject layout")
        self.cB.clicked.connect(self.reject)

        grid = QGridLayout()
        grid.addWidget(self.sdfB, 0, 1)
        grid.addWidget(self.asdB, 0, 2)
        grid.addWidget(self.frB, 0, 3)
        grid.addWidget(self.vB, 5, 3)
        grid.addWidget(self.cB, 6, 1)
        grid.addWidget(self.aB, 6, 3)
        ##
        grid.addWidget(self.deleteLabel, 1, 1)
        grid.addWidget(self.moveLabel, 2, 1)
        grid.addWidget(self.zoomLabel, 3, 1)
        grid.addWidget(self.deleteKey, 1, 2)
        grid.addWidget(self.moveKey, 2, 2)
        grid.addWidget(self.zoomKey, 3, 2)
        ##
        grid.addWidget(self.previousToolLabel, 1, 3)
        grid.addWidget(self.previousToolKey, 1, 4)
        grid.addWidget(self.nextToolLabel, 1, 7)
        grid.addWidget(self.nextToolKey, 1, 8)
        ##
        grid.addWidget(self.previousPaneLabel, 4, 3)
        grid.addWidget(self.previousPaneKey, 4, 4)
        grid.addWidget(self.nextPaneLabel, 4, 7)
        grid.addWidget(self.nextPaneKey, 4, 8)
        ##
        grid.addWidget(self.previousRubricLabel, 2, 5)
        grid.addWidget(self.previousRubricKey, 2, 6)
        grid.addWidget(self.nextRubricLabel, 3, 5)
        grid.addWidget(self.nextRubricKey, 3, 6)
        ##
        self.setLayout(grid)

    def setSDF(self):
        for act in self.actions:
            getattr(self, act + "Key").setText(keys_sdf[act])

    def setFR(self):
        for act in self.actions:
            getattr(self, act + "Key").setText(keys_fr[act])

    def setASD(self):
        for act in self.actions:
            getattr(self, act + "Key").setText(keys_asd[act])

    def validate(self):
        actToCode = {}
        for act in self.actions:
            actToCode[act] = getattr(self, act + "Key").theCode
            if actToCode[act] is None:
                ErrorMessage("Is invalid - '{}' is missing a key".format(act)).exec_()
                return False
        # check for duplications
        for n, act in enumerate(self.actions):
            for k in range(0, n):
                if actToCode[act] == actToCode[self.actions[k]]:
                    ErrorMessage(
                        "Is invalid '{}' and '{}' have same key '{}'".format(
                            act,
                            self.actions[k],
                            QKeySequence(actToCode[act]).toString(),
                        )
                    ).exec_()
                    return False
        return True

    def getKeyBindings(self):
        newKeyDict = {}
        for act in self.actions:
            newKeyDict[act] = getattr(self, act + "Key").theKey
        return newKeyDict

    def acceptLayout(self):
        if self.validate() is False:
            return
        self.accept()


def main(args):
    app = QApplication(args)
    kw = KeyWrangler()
    kw.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main([""])
