# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021-2024 Colin B. Macdonald

from copy import deepcopy
import logging
import sys

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

import plom
from .useful_classes import WarnMsg


log = logging.getLogger("keybindings")


stringOfLegalKeys = "qwertyuiop[]asdfghjkl;'zxcvbnm,./"

actions_with_changeable_keys = [
    "prev-rubric",
    "next-rubric",
    "prev-tab",
    "next-tab",
    "prev-tool",
    "next-tool",
    "redo",
    "undo",
    "delete",
    "move",
    "zoom",
]


TODO_other_key_layouts = {
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
}


_keybindings_list = [
    {"name": "default", "file": "default_keys.toml"},
    {"name": "wasd", "file": "wasd_keys.toml"},
    {"name": "ijkl", "file": "ijkl_keys.toml"},
    {"name": "esdf_french", "file": "esdf_french_keys.toml"},
    {
        "name": "custom",
        "long_name": "Custom",
        "file": None,
        "about_html": """
          <p>Changing any key starts a custom overlay.</p>
          <p><b>Warning:</b> this is a beta feature; these customizations
            are <em>not saved</em> when you restart Plom.  Issue #2254.
          </p>
        """,
    },
]


def get_keybindings_list():
    it = deepcopy(_keybindings_list)
    for kb in it:
        f = kb["file"]
        if f is None:
            overlay = {}
        else:
            log.info("Loading keybindings from %s", f)
            with open(resources.files(plom) / f, "rb") as fh:
                overlay = tomllib.load(fh)
        metadata = overlay.pop("__metadata__", {})
        for k, v in metadata.items():
            kb[k] = v
        if kb["name"] != "default":
            kb["overlay"] = overlay
    return it


def get_keybinding_overlay(name):
    _keybindings_dict = {x["name"]: x for x in _keybindings_list}
    keymap = _keybindings_dict[name]
    f = keymap["file"]
    if name == "default" or f is None:
        overlay = {}
    else:
        log.info("Loading keybindings from %s", f)
        with open(resources.files(plom) / f, "rb") as fh:
            overlay = tomllib.load(fh)
    # note copy unnecessary as we have fresh copy from file
    overlay.pop("__metadata__", None)
    return overlay


def get_key_bindings(name, custom_overlay={}):
    """Generate the keybindings from a name and or a custom overlay.

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

    This function is fairly expensive and loads from disc every time.
    Could be refactored to cache the base data and non-custom overlays,
    if it is too slow.
    """
    # TODO: I think plom.client would be better, but can't get it to work
    f = "default_keys.toml"
    log.info("Loading keybindings from %s", f)
    with open(resources.files(plom) / f, "rb") as fh:
        default_keydata = tomllib.load(fh)
    default_keydata.pop("__metadata__")

    _keybindings_dict = {x["name"]: x for x in _keybindings_list}
    keymap = _keybindings_dict[name]
    if name == "custom":
        overlay = custom_overlay
    else:
        f = keymap["file"]
        if name == "default" or f is None:
            overlay = {}
        else:
            log.info("Loading keybindings from %s", f)
            with open(resources.files(plom) / f, "rb") as fh:
                overlay = tomllib.load(fh)
            overlay.pop("__metadata__", None)
        # keymap["overlay"] = overlay
    # note copy unnecessary as we have fresh copy from file
    return compute_keybinding_from_overlay(default_keydata, overlay, copy=False)


def compute_keybinding_from_overlay(base, overlay, *, copy=True):
    # loop over keys in overlay map and push updates into copy of default
    keydata = base
    if copy:
        keydata = deepcopy(keydata)
    for action, dat in overlay.items():
        keydata[action].update(dat)
    return keydata


class KeyEditDialog(QDialog):
    def __init__(self, parent, *, label, info=None, currentKey=None, legal=None):
        """Dialog to edit a single key-binding for an action.

        Very simple; no shift-ctrl etc modifier keys.

        TODO: custom line edit eats enter and esc.

        Args:
            parent (QWidget): what widget to parent this dialog.

        Keyword Args:
            label (str): What action are we changing?
            currentKey (str): the current key to populate the dialog.
                Can be blank or omitted.
            info (str): optional extra information to display.
            legal (str): keys that can entered.  If omitted/empty, use
                a default.

        Returns:
            None
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
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        vb.addWidget(buttons)
        self.setLayout(vb)


class SingleKeyEdit(QLineEdit):
    def __init__(self, parent, currentKey=None, legal=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter)
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
        if keyCode in (
            Qt.Key.Key_Control,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
        ):
            return
        if keyCode in [Qt.Key.Key_Backspace, Qt.Key.Key_Delete]:
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


class KeyWrangler:
    def __init__(self):
        super().__init__()
        self.legalKeyCodes = [QKeySequence(c)[0] for c in stringOfLegalKeys]
        self.actions = actions_with_changeable_keys

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

    @classmethod
    def overlay_warnings(cls, overlay):
        """No duplicates in the overlay itself, although this allows duplicates in the overall keymap."""
        for k in overlay.keys():
            if k not in actions_with_changeable_keys:
                return f'overlay has invalid action "{k}"'
        # argh, keys like keyboard, not like dict indexing
        all_keys = [v["keys"][0] for v in overlay.values()]
        if len(set(all_keys)) != len(all_keys):
            return "Two actions have the same key"
        return None
