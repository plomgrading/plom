# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2022 Andrew Rechnitzer
# Copyright (C) 2021-2023 Colin B. Macdonald

from copy import deepcopy
import logging
import sys

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

from PyQt5.QtCore import Qt, QBuffer, QByteArray
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QKeySequence, QPainter, QPixmap, QMovie
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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import plom
import plom.client.help_img
from .useful_classes import InfoMsg
from .key_wrangler import KeyEditDialog
from .key_wrangler import get_keybinding_overlay, get_key_bindings
from .key_wrangler import get_keybindings_list, actions_with_changeable_keys


log = logging.getLogger("keybindings")


# TODO:
# * no validity checking done
#   - use code from old KeyWrangler
class KeyHelp(QDialog):
    def __init__(self, parent, keybinding_name, *, custom_overlay={}, initial_tab=0):
        """Construct the KeyHelp dialog.

        Args:
            parent (QWidget):
            keybinding_name (str): which keybinding to initially display.

        Keyword args:
            custom_overlay (dict): if there was already a custom keybinding,
               pass its overlay here.  We will copy it, not change it.  This
               is because the user may make local changes and then cancel.
            initial_tab (int): index of the tab we'd like to open on.
        """
        super().__init__(parent)
        self._custom_overlay = deepcopy(custom_overlay)
        vb = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(ClickDragPage(), "Tips")
        self.tabs = tabs

        keybindings = get_keybindings_list()
        (_initial_idx,) = [
            i for i, x in enumerate(keybindings) if x["name"] == keybinding_name
        ]
        # position of the custom map
        (self.CUSTOM_IDX,) = [
            i for i, x in enumerate(keybindings) if x["name"] == "custom"
        ]

        # trigger this to draw the diagrams (which depend on keybinding)
        self.update_keys_by_name(keybinding_name)

        buttons = QHBoxLayout()
        keyLayoutCB = QComboBox()
        keyLayoutCB.addItems([x["long_name"] for x in keybindings])
        keyLayoutCB.setCurrentIndex(_initial_idx)
        keyLayoutCB.currentIndexChanged.connect(self.update_keys_by_idx)
        self._keyLayoutCB = keyLayoutCB
        # messy hack to map index back to name of keybinding
        self._keyLayoutCB_idx_to_name = [x["name"] for x in keybindings]

        buttons.addWidget(keyLayoutCB, 1)
        b = QPushButton("About")
        b.clicked.connect(self.about)
        # not sure why I need this:
        b.setAutoDefault(False)
        buttons.addWidget(b)
        buttons.addSpacing(64)
        buttons.addStretch(2)
        b = QPushButton("&Ok")
        b.clicked.connect(self.accept)
        buttons.addWidget(b)
        vb.addWidget(tabs)
        vb.addLayout(buttons)
        self.setLayout(vb)
        self.tabs.setCurrentIndex(initial_tab)

    def get_selected_keybinding_name(self):
        """Return the name (str) of the selected keybinding."""
        idx = self._keyLayoutCB.currentIndex()
        return self._keyLayoutCB_idx_to_name[idx]

    def update_keys_by_name(self, name):
        keydata = get_key_bindings(name, custom_overlay=self._custom_overlay)
        self.redraw_tables_and_diagrams(keydata)
        # keep a memo of the keydata until we next change it
        self.keydata = keydata

    def update_keys_by_idx(self, idx):
        name = self._keyLayoutCB_idx_to_name[idx]
        self.update_keys_by_name(name)

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
        name = self._keyLayoutCB_idx_to_name[idx]
        if name != "custom":
            # we were not in the custom map; copy current overlay as new custom
            self._custom_overlay = get_keybinding_overlay(name)
        overlay = self._custom_overlay
        A = overlay.get(action, None)
        if A is None:
            overlay[action] = {"keys": [new_key]}
        else:
            log.info("%s updating existing overlay item", action)
            overlay[action]["keys"][0] = new_key
        self._keyLayoutCB.setCurrentIndex(self.CUSTOM_IDX)
        if name == "custom":
            # force redraw if the current index did not change
            self.update_keys_by_name("custom")

    def has_custom_map(self):
        # i.e., is the custom overlay nonempty?
        return bool(self._custom_overlay)

    def get_custom_overlay(self):
        return self._custom_overlay

    def currently_on_custom_map(self):
        idx = self._keyLayoutCB.currentIndex()
        return idx == self.CUSTOM_IDX

    def redraw_tables_and_diagrams(self, keydata):
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

        for label, tw in self.make_ui_tables(keydata).items():
            # special case the first 2 with graphics
            if label == "Rubrics":
                w = QWidget()
                wb = QVBoxLayout()
                d = RubricNavDiagram(keydata)
                d.wants_to_change_key.connect(self.interactively_change_key)
                wb.addWidget(d)
                wb.addWidget(tw)
                w.setLayout(wb)
            elif label == "Annotation":
                w = QWidget()
                wb = QVBoxLayout()
                d = ToolNavDiagram(keydata)
                d.wants_to_change_key.connect(self.interactively_change_key)
                wb.addWidget(d)
                wb.addWidget(tw)
                w.setLayout(wb)
            else:
                w = tw
            self.tabs.addTab(w, accel[label])
        # restore the current tab
        self.tabs.setCurrentIndex(current_tab)

    def make_ui_tables(self, keydata):
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
            # no sorting during insertation, Issue #2065
            tw.setSortingEnabled(False)
            tables[div] = tw
        # loop over all the keys and insert each key to the appropriate table(s)
        for a, dat in keydata.items():
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
                    n,
                    1,
                    QTableWidgetItem(
                        ", ".join(
                            QKeySequence(k).toString(QKeySequence.NativeText)
                            for k in dat["keys"]
                        )
                    ),
                )
                tw.setItem(n, 2, QTableWidgetItem(dat["info"]))

        for k, tw in tables.items():
            tw.setSortingEnabled(True)
            tw.setWordWrap(True)
            tw.resizeRowsToContents()

        return tables

    def about(self):
        txt = """
            <p>Plom uses spatial keyboard shortcuts with a one hand on
            keyboard, one hand on mouse approach.</p>
        """
        keybindings = get_keybindings_list()
        idx = self._keyLayoutCB.currentIndex()
        kb_specific = keybindings[idx].get("about_html", "")
        txt += kb_specific
        InfoMsg(self, txt).exec()


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

    def put_stuff(self, keydata):
        pix = QPixmap()
        res = resources.files(plom.client.help_img) / "nav_rubric.png"
        pix.loadFromData(res.read_bytes())
        self.scene.addPixmap(pix)  # is at position (0,0)

        sheet = "QPushButton { color : teal; font-size: 24pt;}"

        def lambda_factory(w):
            return lambda: self.change_key(w)

        def stuff_it(w, x, y):
            key = QKeySequence(keydata[w]["keys"][0])
            b = QPushButton(key.toString(QKeySequence.NativeText))
            b.setStyleSheet(sheet)
            b.setToolTip(keydata[w]["human"])
            if w in actions_with_changeable_keys:
                b.setToolTip(b.toolTip() + "\n(click to change)")
                b.clicked.connect(lambda_factory(w))
            else:
                # TODO: a downside is the tooltip does not show
                b.setEnabled(False)
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
        res = resources.files(plom.client.help_img) / "nav_tools.png"
        pix.loadFromData(res.read_bytes())
        self.scene.addPixmap(pix)  # is at position (0,0)

        # little helper to extract from keydata
        def key(s):
            return keydata[s]["keys"][0]

        sheet = "QPushButton { color : teal; font-size: 24pt;}"

        def lambda_factory(w):
            return lambda: self.change_key(w)

        def stuff_it(w, x, y):
            key = QKeySequence(keydata[w]["keys"][0])
            b = QPushButton(key.toString(QKeySequence.NativeText))
            b.setStyleSheet(sheet)
            b.setToolTip(keydata[w]["human"])
            if w in actions_with_changeable_keys:
                b.setToolTip(b.toolTip() + "\n(click to change)")
                b.clicked.connect(lambda_factory(w))
            else:
                # TODO: a downside is the tooltip does not show
                b.setEnabled(False)
            li = self.scene.addWidget(b)
            li.setPos(x, y)

        stuff_it("next-tool", 240, 320)
        stuff_it("prev-tool", 40, 320)
        stuff_it("move", 395, 170)
        stuff_it("undo", 120, -40)
        stuff_it("redo", 210, -40)
        stuff_it("help", 350, -30)
        stuff_it("zoom", -40, 15)
        stuff_it("delete", -40, 220)


class ClickDragPage(QWidget):
    def __init__(self):
        super().__init__()
        grid = QVBoxLayout()
        # load the gif from resources - needs a little subterfuge
        # https://stackoverflow.com/questions/71072485/qmovie-from-qbuffer-from-qbytearray-not-displaying-gif
        res = resources.files(plom.client.help_img) / "click_drag.gif"
        film_bytes = QByteArray(res.read_bytes())
        film_buffer = QBuffer(film_bytes)
        film = QMovie()
        film.setDevice(film_buffer)
        film.setCacheMode(QMovie.CacheAll)

        film_label = QLabel()
        film_label.setMovie(film)

        label = QLabel(
            """<p>
            Most tools can <b>highlight a region</b>:
            try click-drag-release-move-click to draw a box and connecting line.
            Works with <tt>tick</tt>, <tt>cross</tt>, <tt>rubric</tt> or <tt>text</tt>.
            </p>"""
        )
        label.setWordWrap(True)
        grid.addSpacing(6)
        grid.addWidget(label)
        grid.addWidget(film_label)
        grid.addSpacing(6)
        label = QLabel(
            """<p>
            Students benefit from this <b>spatial feedback</b>
            as well as specific rubrics.
            </p>"""
        )
        label.setWordWrap(True)
        grid.addWidget(label)
        grid.addSpacing(6)
        label = QLabel(
            """<p>
            Rubrics are reusable and shared between markers.
            You can organize your rubrics into tabs.
            </p>"""
        )
        label.setWordWrap(True)
        grid.addWidget(label)
        grid.addSpacing(6)
        label = QLabel(
            """<p>
            Start your text or rubric with &ldquo;<tt>tex:</tt>&rdquo; to
            render mathematics.  Or press ctrl-enter.
            </p>"""
        )
        label.setWordWrap(True)
        grid.addWidget(label)
        grid.addSpacing(6)
        label = QLabel(
            """<p>
            Try to keep one hand on the keyboard and one on the mouse.
            </p>"""
        )
        label.setWordWrap(True)
        grid.addWidget(label)
        grid.addSpacing(6)

        self.setLayout(grid)
        # as per https://stackoverflow.com/questions/71072485/qmovie-from-qbuffer-from-qbytearray-not-displaying-gif#comment125714355_71072485
        # force film to jump to end to force the qmovie to actually load from the buffer before we
        # return from this function, else buffer closed and will crash qmovie.
        film.jumpToFrame(film.frameCount() - 1)
        film.start()
