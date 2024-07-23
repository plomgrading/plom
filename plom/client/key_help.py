# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2022 Andrew Rechnitzer
# Copyright (C) 2021-2024 Colin B. Macdonald

from __future__ import annotations

from copy import deepcopy
import logging
import sys

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

from PyQt6.QtCore import Qt, QBuffer, QByteArray, QPointF
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QKeySequence,
    QPainter,
    QPainterPath,
    QMovie,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QGraphicsPathItem,
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
    """The KeyHelp dialog shows hints, keyboard shortcuts and allows their customization."""

    def __init__(
        self,
        parent: QWidget,
        keybinding_name: str,
        *,
        custom_overlay: dict = {},
        initial_tab: int = 0,
    ) -> None:
        """Construct the KeyHelp dialog.

        Args:
            parent: what widget to parent this dialog.
            keybinding_name: which keybinding to initially display.

        Keyword Args:
            custom_overlay: if there was already a custom keybinding,
               pass its overlay here.  We will copy it, not change it.  This
               is because the user may make local changes and then cancel.
            initial_tab: index of the tab we'd like to open on.

        Returns:
            None
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
        # do we still get flicker: this still isn't the right way to force resize?
        self.tabs.currentChanged.connect(self._hacky_resizer)

    def _hacky_resizer(self, n: int) -> None:
        # on tab change, we sadly need some hacks to zoom the QGraphicViews
        for thing in self._things_to_hack_zoom:
            thing.resetView()

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
        if diag.exec() != QDialog.DialogCode.Accepted:
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

        self._things_to_hack_zoom = []
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
                self._things_to_hack_zoom.append(d)
            elif label == "Annotation":
                w = QWidget()
                wb = QVBoxLayout()
                d = ToolNavDiagram(keydata)
                d.wants_to_change_key.connect(self.interactively_change_key)
                wb.addWidget(d)
                wb.addWidget(tw)
                w.setLayout(wb)
                self._things_to_hack_zoom.append(d)
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
            tw.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            tw.setAlternatingRowColors(True)
            tw.setHorizontalHeaderLabels(["Function", "Keys", "Description"])
            # TODO: wire double click to omit wants_to_change_key
            tw.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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
                            QKeySequence(k).toString(
                                QKeySequence.SequenceFormat.NativeText
                            )
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


def _label(lambda_factory, scene, keydata, w, x, y, route, d="N", *, sep=(0, 0)):
    # A private helper function: draw a line on scene connecting a certain
    # point to a control, then draw a button and connect its blick to
    # the result of a "lambda_factory" passed in.

    sheet = "QPushButton { background-color : teal; }"
    # sheet = "QPushButton { color : teal; }"

    pen = QPen(QColor("teal"), 4)
    p = QPainterPath()
    p.moveTo(x, y)
    p.addEllipse(QPointF(x, y), 4, 4)
    p.moveTo(x, y)
    for dx, dy in route:
        x += dx
        y += dy
        p.lineTo(x, y)
    p.addEllipse(QPointF(x, y), 4, 4)

    pi = QGraphicsPathItem()
    pi.setPath(p)
    scene.addItem(pi)
    pi.setPen(pen)

    # extra gap between end and button
    x += sep[0]
    y += sep[1]

    key = QKeySequence(keydata[w]["keys"][0])
    b = QPushButton(key.toString(QKeySequence.SequenceFormat.NativeText))
    b.setStyleSheet(sheet)
    b.setToolTip(keydata[w]["human"])
    if w in actions_with_changeable_keys:
        b.setToolTip(b.toolTip() + "\n(click to change)")
        b.clicked.connect(lambda_factory(w))
    else:
        # TODO: a downside is the tooltip does not show
        b.setEnabled(False)
    li = scene.addWidget(b)
    # li.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
    li.setScale(1.66)
    br = li.mapRectToScene(li.boundingRect())
    label_offset = 8
    if d == "N":
        x -= br.width() / 2
        y -= br.height()
        y -= label_offset
    elif d == "S":
        x -= br.width() / 2
        y += label_offset
    elif d == "W":
        x -= br.width()
        x -= label_offset
        y -= br.height() / 2
    elif d == "E":
        x += label_offset
        y -= br.height() / 2
    else:
        raise NotImplementedError("No such direction")
    li.setPos(x, y)


class RubricNavDiagram(QFrame):
    """A page for our inline help about changing rubrics with keyboard shortcuts."""

    wants_to_change_key = pyqtSignal(str)

    def __init__(self, keydata):
        super().__init__()
        # self.setFrameShape(QFrame.Shape.Panel)
        view = QGraphicsView()
        view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        view.setFrameShape(QFrame.Shape.NoFrame)

        self.scene = QGraphicsScene()
        self.put_stuff(keydata)
        view.setScene(self.scene)
        # seems to effect the balance of graphic to bottom list
        view.scale(0.6, 0.6)
        self._view = view

        grid = QVBoxLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(view)
        self.setLayout(grid)
        # ugh, this bullshit again
        # TODO: but it won't help: tab not rendered immediately :(
        # QTimer.singleShot(500, self.resetView)

    def resetView(self):
        # Ensure the graphic fits in view with a border around.
        # (asymmetric border looked better with particular locations of buttons)
        self._view.fitInView(
            self.scene.sceneRect().adjusted(-40, -10, 20, 10),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def resizeEvent(self, event):
        self.resetView()

    def change_key(self, action):
        self.wants_to_change_key.emit(action)

    def put_stuff(self, keydata):
        pix = QPixmap()
        res = resources.files(plom.client.help_img) / "nav_rubric.png"
        pix.loadFromData(res.read_bytes())
        self.scene.addPixmap(pix)  # is at position (0,0)

        def lambda_factory(w):
            # the factory returns a function to change a keybinding
            return lambda: self.change_key(w)

        def label(*args, **kwargs):
            # specialize the generic helper fcn to this scene and keydata
            _label(lambda_factory, self.scene, keydata, *args, **kwargs)

        # then use that helper function to label the controls in the picture
        r = 12  # radius of turns
        d = 38  # unit distance
        label("prev-rubric", 626, 215, ((2 * d, 0), (r, -r), (0, -d)), "N")
        label("next-rubric", 626, 215, ((2 * d, 0), (r, r), (0, d)), "S")
        label("prev-tab", 231, 18, ((0, -d), (-r, -r), (-d, 0)), "W")
        label("next-tab", 231, 18, ((0, -d), (r, -r), (d, 0)), "E")


class ToolNavDiagram(QFrame):
    """A page for our inline help about changing tools with keyboard shortcuts."""

    wants_to_change_key = pyqtSignal(str)

    def __init__(self, keydata):
        super().__init__()
        # self.setFrameShape(QFrame.Shape.Panel)
        view = QGraphicsView()
        view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        view.setFrameShape(QFrame.Shape.NoFrame)

        self.scene = QGraphicsScene()
        self.put_stuff(keydata)
        view.setScene(self.scene)
        # seems to effect the balance of graphic to bottom list
        view.scale(0.6, 0.6)
        self._view = view

        grid = QVBoxLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(view)
        self.setLayout(grid)

    def resetView(self):
        # Ensure the graphic fits in view with a border around.
        self._view.fitInView(
            self.scene.sceneRect().adjusted(-20, -10, 20, 10),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def resizeEvent(self, event):
        self.resetView()

    def change_key(self, action):
        self.wants_to_change_key.emit(action)

    def put_stuff(self, keydata):
        pix = QPixmap()
        res = resources.files(plom.client.help_img) / "nav_tools.png"
        pix.loadFromData(res.read_bytes())
        self.scene.addPixmap(pix)  # is at position (0,0)

        def lambda_factory(w):
            # the factory returns a function to change a keybinding
            return lambda: self.change_key(w)

        def lbl(*args, **kwargs):
            # specialize the generic helper fcn to this scene and keydata
            _label(lambda_factory, self.scene, keydata, *args, **kwargs)

        # then use that helper function to label the controls in the picture
        r = 10  # radius of turns
        d = 36  # unit distance
        lbl("next-tool", 266, 385, ((0, d), (r, r), (d, 0)), "E")
        lbl("prev-tool", 266, 385, ((0, d), (-r, r), (-d, 0)), "W")
        lbl("move", 560, 254, ((0, d / 2), (r, r), (2 * d, 0)), "E")
        lbl("undo", 309, 233, ((-25, 0), (-r, -r), (0, -6.5 * d)), "N", sep=(-d, 0))
        lbl("redo", 333, 233, ((25, 0), (r, -r), (0, -6.5 * d)), "N", sep=(d, 0))
        lbl("help", 630, 98, ((d, 0), (r, -r), (0, -1.5 * d)), "N", sep=(d, 0))
        lbl("zoom", 257, 150, ((-7.8 * d, 0), (-r, -r), (0, -2 * d)), "N", sep=(-d, 0))
        lbl("delete", 10, 230, ((-d, 0), (-r, r), (0, d)), "S", sep=(-d, 0))


class ClickDragPage(QWidget):
    """A page for our inline help about click-drag and other hints."""

    def __init__(self) -> None:
        super().__init__()
        grid = QVBoxLayout()
        # load the gif from resources - needs a little subterfuge
        # https://stackoverflow.com/questions/71072485/qmovie-from-qbuffer-from-qbytearray-not-displaying-gif
        res = resources.files(plom.client.help_img) / "click_drag.gif"
        film_qbytesarray = QByteArray(res.read_bytes())
        film_qbuffer = QBuffer(film_qbytesarray)
        film = QMovie()
        film.setDevice(film_qbuffer)
        film.setCacheMode(QMovie.CacheMode.CacheAll)

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
        # as per link above, try to force QMove to load from the buffer before the
        # buffer and bytearray are closed and/or garbage collected
        film.jumpToFrame(film.frameCount() - 1)
        film.jumpToFrame(0)
        film.start()
        # But it seems in PyQt6 (at least Qt6-6.7.1) we need ref to prevent SIGSEGV
        # Note Qt docs: "QBuffer doesn't take ownership of the QByteArray"
        self._film_buffer = film_qbuffer
        self._film_bytesarray = film_qbytesarray
