# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2022 Andrew Rechnitzer
# Copyright (C) 2021-2022 Colin B. Macdonald

from copy import deepcopy
import importlib.resources as resources
import logging

import toml
from PyQt5.QtCore import Qt, QBuffer, QByteArray
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPainter, QPixmap, QMovie
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
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

import plom
import plom.client.help_img
from .key_wrangler import KeyEditDialog
from .key_wrangler import get_key_bindings, _keybindings_list


log = logging.getLogger("keybindings")


# TODO:
# * duplicates a lot of code from key_wrangler:
#   - replace self.keybindings with some calls from there?
#   - use get_key_bindings
# * no validity checking done
#   - use code from old KeyWrangler
class KeyHelp(QDialog):
    def __init__(self, parent, *, keybinding_name, custom_overlay={}):
        """Construct the KeyHelp dialog.

        Args:
            parent (QWidget):

        Keyword args:
            keybinding_name (str): which keybinding to initially display.
            custom_overlay (dict): if there was already a custom keybinding,
               pass its overlay here.  We will copy it not change it.
        """
        super().__init__(parent)
        vb = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(ClickDragPage(), "Tips")

        self.default_keydata, self.keybindings = self.load_keymaps(_keybindings_list, custom_overlay)

        self.tabs = tabs
        if keybinding_name:
            # TODO: how about self.update_keybinding_by_name?
            (prev_keymap_idx,) = [
                i
                for i, x in enumerate(_keybindings_list)
                if x["name"] == keybinding_name
            ]
        self.update_keys(prev_keymap_idx)

        buttons = QHBoxLayout()
        b = QPushButton("&Ok")
        b.clicked.connect(self.accept)
        keyLayoutCB = QComboBox()
        keyLayoutCB.addItems([x["human"] for x in _keybindings_list])
        keyLayoutCB.setCurrentIndex(prev_keymap_idx)
        keyLayoutCB.currentIndexChanged.connect(self.update_keys)
        self._keyLayoutCB = keyLayoutCB
        # messy hack to map index back to name of keybinding
        self._keyLayoutCB_idx_to_name = [x["name"] for x in _keybindings_list]

        buttons.addWidget(keyLayoutCB, 1)
        buttons.addSpacing(64)
        buttons.addStretch(2)
        buttons.addWidget(b)
        vb.addWidget(tabs)
        vb.addLayout(buttons)
        self.setLayout(vb)

    # TODO: hardcoded position of the custom map
    CUSTOM_IDX = 3

    def get_selected_keybinding_name(self):
        """Return the name (str) of the selected keybinding."""
        idx = self._keyLayoutCB.currentIndex()
        return self._keyLayoutCB_idx_to_name[idx]

    def load_keymaps(self, keybindings, custom_overlay):
        # TODO: I think plom.client would be better, put can't get it to work
        f = "default_keys.toml"
        log.info("Loading keybindings from %s", f)
        default_keydata = toml.loads(resources.read_text(plom, f))

        keybindings = deepcopy(keybindings)
        for keymap in keybindings:
            f = keymap["file"]
            if f is None:
                overlay = {}
            else:
                log.info("Loading keybindings from %s", f)
                overlay = toml.loads(resources.read_text(plom, f))
            if keymap["name"] == "custom":
                overlay = deepcopy(custom_overlay)
            keymap["overlay"] = overlay
        return default_keydata, keybindings

    def update_keys(self, idx):
        overlay = self.keybindings[idx]["overlay"]
        # loop over keys in overlay map and push updates into copy of default
        self.keydata = deepcopy(self.default_keydata)
        for action, dat in overlay.items():
            self.keydata[action].update(dat)
        self.change_keybindings()

    def interactively_change_key(self, action):
        info = ""
        if self.has_custom_map() and not self.currently_on_custom_map():
            info = """<p><b>Note:</b> there is already a custom keymap.
                Changing this keybinding will replace it; or you can
                cancel, select the &ldquo;Custom&rdquo; map and edit.</p>
            """
        dat = self.keydata[action]
        old_key = dat["keys"][0]
        diag = KeyEditDialog(self, label=dat["human"], currentKey=old_key, info=info)
        if diag.exec() != QDialog.Accepted:
            return
        new_key = diag._keyedit.text()
        if new_key == old_key:
            return
        log.info(f"diagram: {action} changing key from {old_key} to {new_key}")
        # TODO: check validity (no dupe keys etc, maybe use KeyWrangler code)
        self.change_key(action, new_key)

    def change_key(self, action, new_key):
        idx = self._keyLayoutCB.currentIndex()
        if idx == self.CUSTOM_IDX:
            # we're already in the custom map, so just update
            overlay = self.keybindings[self.CUSTOM_IDX]["overlay"]
        else:
            # we were not in the custom map; copy current overlay as new custom
            overlay = deepcopy(self.keybindings[idx]["overlay"])
            self.keybindings[self.CUSTOM_IDX]["overlay"] = overlay
        A = overlay.get(action, None)
        if A is None:
            overlay[action] = {"keys": [new_key]}
        else:
            log.info("%s updating existing overlay item", action)
            overlay[action]["keys"][0] = new_key
        self._keyLayoutCB.setCurrentIndex(self.CUSTOM_IDX)
        if idx == self.CUSTOM_IDX:
            # force redraw if the current index did not change
            self.update_keys(self.CUSTOM_IDX)

    def has_custom_map(self):
        return bool(self.keybindings[self.CUSTOM_IDX]["overlay"])

    def get_custom_overlay(self):
        return self.keybindings[self.CUSTOM_IDX]["overlay"]

    def currently_on_custom_map(self):
        idx = self._keyLayoutCB.currentIndex()
        return idx == self.CUSTOM_IDX

    def change_keybindings(self):
        accel = {
            k: v
            for k, v in zip(
                ("Rubrics", "Annotation", "General", "Text", "View", "All"),
                ("&Rubrics", "&Annotation", "&General", "&Text", "&View", "A&ll"),
            )
        }
        # Loop and delete the exists tabs (if any) but not the first "tips" tab
        # Note: important to removeTab() or setCurrentIndex doesn't work
        current_tab = self.tabs.currentIndex()
        while self.tabs.count() > 1:
            w = self.tabs.widget(1)
            w.deleteLater()
            self.tabs.removeTab(1)

        for label, tw in self.make_ui_tables().items():
            # special case the first 2 with graphics
            if label == "Rubrics":
                w = QWidget()
                wb = QVBoxLayout()
                d = RubricNavDiagram(self.keydata)
                d.wants_to_change_key.connect(self.interactively_change_key)
                wb.addWidget(d)
                wb.addWidget(tw)
                w.setLayout(wb)
            elif label == "Annotation":
                w = QWidget()
                wb = QVBoxLayout()
                d = ToolNavDiagram(self.keydata)
                d.wants_to_change_key.connect(self.interactively_change_key)
                wb.addWidget(d)
                wb.addWidget(tw)
                w.setLayout(wb)
            else:
                w = tw
            self.tabs.addTab(w, accel[label])
        # restore the current tab
        self.tabs.setCurrentIndex(current_tab)

    def make_ui_tables(self):
        """Make some Qt tables with tables of key bindings.

        Returns:
            dict: keys are `str` for category and values are `QTableWdiget`.
        """
        tables = {}
        # build one table for each division
        for div in ["Rubrics", "Annotation", "General", "Text", "View", "All"]:
            tw = QTableWidget()
            tw.setColumnCount(3)
            tw.verticalHeader().hide()
            tw.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            tw.setAlternatingRowColors(True)
            tw.setHorizontalHeaderLabels(["Function", "Keys", "Description"])
            # TODO: wire double click to omit wants_to_change_key
            tw.setEditTriggers(QAbstractItemView.NoEditTriggers)
            # no sorting during insertation please TODO issue number
            tw.setSortingEnabled(False)
            tables[div] = tw
        # loop over all the keys and insert each key to the appropriate table(s)
        for a, dat in self.keydata.items():
            for cat in set(dat["categories"]).union(("All",)):
                try:
                    tw = tables[cat]
                except KeyError:
                    log.info(
                        f"action {a} is in category {cat} which is not in UI tables"
                    )
                    continue
                n = tw.rowCount()
                tw.insertRow(n)
                tw.setItem(n, 0, QTableWidgetItem(dat["human"]))
                tw.setItem(
                    n, 1, QTableWidgetItem(", ".join(str(k) for k in dat["keys"]))
                )
                tw.setItem(n, 2, QTableWidgetItem(dat["info"]))

        for k, tw in tables.items():
            tw.setSortingEnabled(True)
            tw.setWordWrap(True)
            tw.resizeRowsToContents()

        return tables


class RubricNavDiagram(QFrame):
    wants_to_change_key = pyqtSignal(str)

    def __init__(self, keydata):
        super().__init__()
        # self.setFrameShape(QFrame.Panel)
        view = QGraphicsView()
        view.setRenderHint(QPainter.Antialiasing, True)
        view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # view.setFrameShape(QFrame.NoFrame)

        self.scene = QGraphicsScene()
        self.put_stuff(keydata)
        view.setScene(self.scene)
        view.fitInView(
            self.scene.sceneRect().adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio
        )

        grid = QVBoxLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(view)
        self.setLayout(grid)

    def change_key(self, action):
        self.wants_to_change_key.emit(action)

    def put_stuff(self, action):
        pix = QPixmap()
        pix.loadFromData(resources.read_binary(plom.client.help_img, "nav_rubric.png"))
        self.scene.addPixmap(pix)  # is at position (0,0)

        sheet = "QPushButton { color : teal; font-size: 24pt;}"

        def lambda_factory(w):
            return lambda: self.change_key(w)

        def stuff_it(w, x, y):
            b = QPushButton(action[w]["keys"][0])
            b.setStyleSheet(sheet)
            b.setToolTip(f'{action[w]["human"]}\n(click to change)')
            b.clicked.connect(lambda_factory(w))
            li = self.scene.addWidget(b)
            li.setPos(x, y)

        stuff_it("next-rubric", 340, 250)
        stuff_it("prev-rubric", 340, 70)
        stuff_it("prev-tab", -40, -10)
        stuff_it("next-tab", 160, -10)


class ToolNavDiagram(QFrame):
    wants_to_change_key = pyqtSignal(str)

    def __init__(self, keydata):
        super().__init__()
        # self.setFrameShape(QFrame.Panel)
        view = QGraphicsView()
        view.setRenderHint(QPainter.Antialiasing, True)
        view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # view.setFrameShape(QFrame.NoFrame)

        self.scene = QGraphicsScene()
        self.put_stuff(keydata)
        view.setScene(self.scene)
        view.fitInView(
            self.scene.sceneRect().adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio
        )

        grid = QVBoxLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(view)
        self.setLayout(grid)

    def change_key(self, action):
        self.wants_to_change_key.emit(action)

    def put_stuff(self, keydata):
        pix = QPixmap()
        pix.loadFromData(resources.read_binary(plom.client.help_img, "nav_tools.png"))
        self.scene.addPixmap(pix)  # is at position (0,0)

        # little helper to extract from keydata
        def key(s):
            return keydata[s]["keys"][0]

        sheet = "QPushButton { color : teal; font-size: 24pt;}"

        def lambda_factory(w):
            return lambda: self.change_key(w)

        def stuff_it(w, x, y):
            b = QPushButton(keydata[w]["keys"][0])
            b.setStyleSheet(sheet)
            b.setToolTip(f'{keydata[w]["human"]}\n(click to change)')
            b.clicked.connect(lambda_factory(w))
            li = self.scene.addWidget(b)
            li.setPos(x, y)

        stuff_it("next-tool", 240, 320)
        stuff_it("prev-tool", 40, 320)
        stuff_it("move", 395, 170)
        stuff_it("undo", 120, -40)
        stuff_it("redo", 210, -40)
        # TODO: check whether these are customizable
        stuff_it("help", 350, -30)
        stuff_it("zoom", -40, 15)
        stuff_it("delete", -40, 220)


class ClickDragPage(QWidget):
    def __init__(self):
        super().__init__()
        grid = QVBoxLayout()
        # load the gif from resources - needs a little subterfuge
        # https://stackoverflow.com/questions/71072485/qmovie-from-qbuffer-from-qbytearray-not-displaying-gif

        film_bytes = QByteArray(
            resources.read_binary(plom.client.help_img, "click_drag.gif")
        )
        film_buffer = QBuffer(film_bytes)
        film = QMovie()
        film.setDevice(film_buffer)
        film.setCacheMode(QMovie.CacheAll)

        film_label = QLabel()
        film_label.setMovie(film)
        grid.addWidget(
            QLabel(
                "Click-drag-release-move-click to highlight a region, and stamp rubric with a connecting line."
            )
        )
        grid.addWidget(film_label)
        grid.addSpacing(6)
        grid.addWidget(
            QLabel(
                "Students benefit from spatial feedback (as above) and the use of specific rubrics."
            )
        )
        grid.addSpacing(6)
        grid.addWidget(QLabel("Rubrics are shared between markers."))
        grid.addSpacing(6)
        grid.addWidget(
            QLabel("Try to keep one hand on the keyboard and one on the mouse.")
        )
        grid.addSpacing(6)

        self.setLayout(grid)
        # as per https://stackoverflow.com/questions/71072485/qmovie-from-qbuffer-from-qbytearray-not-displaying-gif#comment125714355_71072485
        # force film to jump to end to force the qmovie to actually load from the buffer before we
        # return from this function, else buffer closed and will crash qmovie.
        film.jumpToFrame(film.frameCount() - 1)
        film.start()
