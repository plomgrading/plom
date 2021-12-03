# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021 Colin B. Macdonald

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QDialog,
    QGroupBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from .useful_classes import ErrorMessage


stringOfLegalKeys = "qwertyuiop[]asdfghjkl;'zxcvbnm,./"

the_actions = [
    "previousRubric",
    "nextRubric",
    "previousTab",
    "nextTab",
    "previousTool",
    "nextTool",
    "redo",
    "undo",
    "delete",
    "move",
    "zoom",
]


key_layouts = {
    "sdf": {
        "redo": "T",
        "undo": "G",
        "nextRubric": "D",
        "previousRubric": "E",
        "nextTab": "F",
        "previousTab": "S",
        "nextTool": "R",
        "previousTool": "W",
        "delete": "Q",
        "move": "A",
        "zoom": "Z",
    },
    "sdf_french": {
        "redo": "T",
        "undo": "G",
        "nextRubric": "D",
        "previousRubric": "E",
        "nextTab": "F",
        "previousTab": "S",
        "nextTool": "R",
        "previousTool": "Z",
        "delete": "A",
        "move": "Q",
        "zoom": "W",
    },
    "dvorak": {
        "redo": "Y",
        "undo": "I",
        "nextRubric": "E",
        "previousRubric": ".",
        "nextTab": "U",
        "previousTab": "O",
        "nextTool": "P",
        "previousTool": ",",
        "delete": "'",
        "move": "A",
        "zoom": ";",
    },
    "asd": {
        "redo": "R",
        "undo": "F",
        "nextRubric": "S",
        "previousRubric": "W",
        "nextTab": "D",
        "previousTab": "A",
        "nextTool": "E",
        "previousTool": "Q",
        "delete": "C",
        "move": "X",
        "zoom": "Z",
    },
    "jkl": {
        "redo": "Y",
        "undo": "H",
        "nextRubric": "K",
        "previousRubric": "I",
        "nextTab": "L",
        "previousTab": "J",
        "nextTool": "O",
        "previousTool": "U",
        "delete": "P",
        "move": ";",
        "zoom": "/",
    },
}


class SingleKeyEdit(QLineEdit):
    def __init__(self, parent, currentKey=None, legal=None):
        super().__init__(parent)
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
    def __init__(self, parent, currentKeys=None):
        super().__init__(parent)
        if currentKeys is None:
            currentKeys = key_layouts["sdf"]
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
        self.sdfB.clicked.connect(lambda: self.setKeyLayout("sdf"))
        self.asdB = QPushButton("Set ASD")
        self.asdB.clicked.connect(lambda: self.setKeyLayout("asd"))
        self.jklB = QPushButton("Set JKL")
        self.jklB.clicked.connect(lambda: self.setKeyLayout("jkl"))
        self.frenchB = QPushButton("Set SDF (French)")
        self.frenchB.clicked.connect(lambda: self.setKeyLayout("sdf_french"))
        self.dvkB = QPushButton("Set Dvorak")
        self.dvkB.clicked.connect(lambda: self.setKeyLayout("dvorak"))
        self.vB = QPushButton("Validate")
        self.vB.clicked.connect(self.validate)
        self.aB = QPushButton("Accept layout")
        self.aB.clicked.connect(self.acceptLayout)
        self.cB = QPushButton("Reject layout")
        self.cB.clicked.connect(self.reject)
        self.GB = QGroupBox("Actions and Keys")

        grid = QGridLayout()
        mgrid = QGridLayout()
        mgrid.addWidget(self.sdfB, 5, 6)
        mgrid.addWidget(self.asdB, 5, 7)
        mgrid.addWidget(self.jklB, 6, 6)
        mgrid.addWidget(self.dvkB, 6, 7)
        mgrid.addWidget(self.frenchB, 5, 8)
        mgrid.addWidget(self.vB, 5, 3)
        mgrid.addWidget(self.cB, 6, 1)
        mgrid.addWidget(self.aB, 6, 3)
        mgrid.addWidget(self.GB, 1, 1, 3, 8)
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
        grid.addWidget(self.previousTabLabel, 4, 3)
        grid.addWidget(self.previousTabKey, 4, 4)
        grid.addWidget(self.nextTabLabel, 4, 7)
        grid.addWidget(self.nextTabKey, 4, 8)
        ##
        grid.addWidget(self.previousRubricLabel, 2, 5)
        grid.addWidget(self.previousRubricKey, 2, 6)
        grid.addWidget(self.nextRubricLabel, 3, 5)
        grid.addWidget(self.nextRubricKey, 3, 6)
        ##
        self.GB.setLayout(grid)
        self.setLayout(mgrid)

    def setKeyLayout(self, name):
        if name not in key_layouts:
            return
        else:
            for act in self.actions:
                getattr(self, act + "Key").setText(key_layouts[name][act])

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
