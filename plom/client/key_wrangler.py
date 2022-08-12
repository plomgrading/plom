# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021-2022 Colin B. Macdonald

from copy import deepcopy
import importlib.resources as resources
import logging

import toml
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

import plom
from .useful_classes import WarnMsg


log = logging.getLogger("keybindings")


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


# todo: decide on keeping just one of these two
_keybindings_dict = {
    "default": {"human": 'Default ("esdf", touch-typist)', "file": None},
    "wasd": {"human": '"wasd" (gamer)', "file": "wasd_keys.toml"},
    "ijkl": {"human": '"ijkl" (left-hand mouse)', "file": "ijkl_keys.toml"},
    "custom": {"human": "Custom", "file": None},
}
_keybindings_list = [
    {"name": "default", "human": 'Default ("esdf", touch-typist)', "file": None},
    {"name": "wasd", "human": '"wasd" (gamer)', "file": "wasd_keys.toml"},
    {"name": "ijkl", "human": '"ijkl" (left-hand mouse)', "file": "ijkl_keys.toml"},
    {"name": "custom", "human": "Custom", "file": None},
]


def get_key_bindings(name, custom_overlay={}):
    """Generate the keybings from a name and or a custom overlay.

    Args:
        name (str): which keybindings to use.

    Keyword Args:.
        custom_overlay (dict): if name is ``"custom"`` then take
            additional shortcut keys from this dict on top of the
            default bindings.  If name isn't ``"custom"`` then
            this input is ignored.

    Returns:
        dict: TODO explain the full keybindings.  The intention is
        not to store this but instead to store only the "overlay"
        and recompute this when needed.

    This function is fairly expensive and loads from disc everytime.
    Could be refactored to cache the base data and non-custom overlays,
    if it is too slow.
    """
    # TODO: I think plom.client would be better, but can't get it to work
    f = "default_keys.toml"
    log.info("Loading keybindings from %s", f)
    default_keydata = toml.loads(resources.read_text(plom, f))

    keymap = _keybindings_dict[name]
    if name == "custom":
        overlay = custom_overlay
    else:
        f = keymap["file"]
        if f is None:
            overlay = {}
        else:
            log.info("Loading keybindings from %s", f)
            overlay = toml.loads(resources.read_text(plom, f))
        # keymap["overlay"] = overlay
    keydata = default_keydata
    # keydata = deepcopy(default_keydata)
    for action, dat in overlay.items():
        keydata[action].update(dat)
    return keydata


def compute_keybinding_from_overlay(base, overlay):
    # loop over keys in overlay map and push updates into copy of default
    keydata = deepcopy(base)
    for action, dat in overlay.items():
        keydata[action].update(dat)


class KeyEditDialog(QDialog):
    def __init__(self, parent, *, label, info=None, currentKey=None, legal=None):
        """Dialog to edit a single key-binding for an action.

        Very simple; no shift-ctrl etc modifier keys.

        TODO: custom line edit eats enter and esc.

        Args:
            parent (QWidget)

        Keyword Args:
            label (str): What action are we changing?
            currentKey (str): the current key to populate the dialog.
                Can be blank or omitted.
            info (str): optional extra information to display.
            legal (str): keys that can entered.  If omitted/empty, use
                a default.
        """
        super().__init__(parent)
        vb = QVBoxLayout()
        vb.addWidget(QLabel(f"Change key for <em>{label}</em>"))
        if not legal:
            legal = stringOfLegalKeys
        legal = [QKeySequence(c)[0] for c in legal]
        self._keyedit = SingleKeyEdit(self, currentKey, legal)
        vb.addWidget(self._keyedit)
        if info:
            label = QLabel(info)
            label.setWordWrap(True)
            vb.addWidget(label)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vb.addWidget(buttons)
        self.setLayout(vb)


class SingleKeyEdit(QLineEdit):
    def __init__(self, parent, currentKey=None, legal=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignHCenter)
        if legal is None:
            legal = []
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
                WarnMsg(self, f"Is invalid - '{act}' is missing a key").exec()
                return False
        # check for duplications
        for n, act in enumerate(self.actions):
            for k in range(0, n):
                if actToCode[act] == actToCode[self.actions[k]]:
                    WarnMsg(
                        self,
                        "Is invalid '{}' and '{}' have same key '{}'".format(
                            act,
                            self.actions[k],
                            QKeySequence(actToCode[act]).toString(),
                        ),
                    ).exec()
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
