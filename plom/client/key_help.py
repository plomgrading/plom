# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2022 Andrew Rechnitzer
# Copyright (C) 2021-2022 Colin B. Macdonald

from copy import deepcopy
import importlib.resources as resources
import logging

import toml
from PyQt5.QtCore import Qt, QBuffer, QByteArray
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


log = logging.getLogger("keybindings")


class KeyHelp(QDialog):
    def __init__(self, parent, *, prev_keymap_idx=0):
        """Construct the KeyHelp dialog.

        Args:
            parent (QWidget):

        Keyword args:
            prev_keymap_idx (int): which keymap to initially display.
        """
        super().__init__(parent)
        vb = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(ClickDragPage(), "Tips")

        self.default_keydata, self.keybindings = self.load_keymaps()
        self.tabs = tabs
        self.update_keys(prev_keymap_idx)

        buttons = QHBoxLayout()
        b = QPushButton("&Ok")
        b.clicked.connect(self.accept)
        keyLayoutCB = QComboBox()
        keyLayoutCB.addItems([x["human"] for x in self.keybindings])
        keyLayoutCB.setCurrentIndex(prev_keymap_idx)
        keyLayoutCB.currentIndexChanged.connect(self.update_keys)

        buttons.addWidget(keyLayoutCB, 1)
        buttons.addWidget(QLabel("(not yet functional)"))
        buttons.addSpacing(64)
        buttons.addStretch(2)
        buttons.addWidget(b)
        vb.addWidget(tabs)
        vb.addLayout(buttons)
        self.setLayout(vb)

    def load_keymaps(self):
        # TODO: I think plom.client would be better, put can't get it to work
        f = "default_keys.toml"
        log.info("Loading keybindings from %s", f)
        default_keydata = toml.loads(resources.read_text(plom, f))

        keybindings = [
            {"human": 'Default ("esdf", touch-typist)', "file": None},
            {"human": '"wasd" (gamer)', "file": "wasd_keys.toml"},
            {"human": '"ijkl" (left-hand mouse)', "file": "ijkl_keys.toml"},
            {"human": "Custom", "file": None},
        ]

        for keymap in keybindings:
            f = keymap["file"]
            if f is None:
                overlay = {}
            else:
                log.info("Loading keybindings from %s", f)
                overlay = toml.loads(resources.read_text(plom, f))
            keymap["overlay"] = overlay
        return default_keydata, keybindings

    def update_keys(self, idx):
        overlay = self.keybindings[idx]["overlay"]
        # loop over keys in overlay map and push updates into copy of default
        self.keydata = deepcopy(self.default_keydata)
        for action, dat in overlay.items():
            self.keydata[action].update(dat)
        self.change_keybindings()

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
                wb.addWidget(RubricNavDiagram(self.keydata))
                wb.addWidget(tw)
                w.setLayout(wb)
            elif label == "Annotation":
                w = QWidget()
                wb = QVBoxLayout()
                wb.addWidget(ToolNavDiagram(self.keydata))
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

    def put_stuff(self, action):
        pix = QPixmap()
        pix.loadFromData(resources.read_binary(plom.client.help_img, "nav_rubric.png"))
        self.scene.addPixmap(pix)  # is at position (0,0)

        sheet = "QPushButton { color : teal; font-size: 24pt;}"

        self.rn = QPushButton(action["next-rubric"]["keys"][0])
        self.rn.setStyleSheet(sheet)
        self.rn.setToolTip("Select next rubic")
        li = self.scene.addWidget(self.rn)
        li.setPos(340, 250)

        self.rp = QPushButton(action["prev-rubric"]["keys"][0])
        self.rp.setStyleSheet(sheet)
        self.rp.setToolTip("Select previous rubic")
        li = self.scene.addWidget(self.rp)
        li.setPos(340, 70)

        self.tp = QPushButton(action["prev-tab"]["keys"][0])
        self.tp.setStyleSheet(sheet)
        self.tp.setToolTip("Select previous tab of rubrics")
        li = self.scene.addWidget(self.tp)
        li.setPos(-40, -10)

        self.tn = QPushButton(action["next-tab"]["keys"][0])
        self.tn.setStyleSheet(sheet)
        self.tn.setToolTip("Select next tab of rubrics")
        li = self.scene.addWidget(self.tn)
        li.setPos(160, -10)


class ToolNavDiagram(QFrame):
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

    def put_stuff(self, keydata):
        pix = QPixmap()
        pix.loadFromData(resources.read_binary(plom.client.help_img, "nav_tools.png"))
        self.scene.addPixmap(pix)  # is at position (0,0)

        # little helper to extract from keydata
        def key(s):
            return keydata[s]["keys"][0]

        sheet = "QPushButton { color : teal; font-size: 24pt;}"

        self.tn = QPushButton(key("next-tool"))
        self.tn.setStyleSheet(sheet)
        self.tn.setToolTip("Select next tool")
        li = self.scene.addWidget(self.tn)
        li.setPos(240, 320)

        self.tp = QPushButton(key("prev-tool"))
        self.tp.setStyleSheet(sheet)
        self.tp.setToolTip("Select previous tool")
        li = self.scene.addWidget(self.tp)
        li.setPos(40, 320)

        self.mv = QPushButton(key("move"))
        self.mv.setStyleSheet(sheet)
        self.mv.setToolTip("Select move tool")
        li = self.scene.addWidget(self.mv)
        li.setPos(395, 170)

        self.ud = QPushButton(key("undo"))
        self.ud.setStyleSheet(sheet)
        self.ud.setToolTip("Undo last action")
        li = self.scene.addWidget(self.ud)
        li.setPos(120, -40)

        self.rd = QPushButton(key("redo"))
        self.rd.setStyleSheet(sheet)
        self.rd.setToolTip("Redo action")
        li = self.scene.addWidget(self.rd)
        li.setPos(210, -40)

        self.hlp = QPushButton(key("help"))
        self.hlp.setStyleSheet(sheet)
        self.hlp.setToolTip("Pop up key help")
        li = self.scene.addWidget(self.hlp)
        li.setPos(350, -30)

        self.zm = QPushButton(key("zoom"))
        self.zm.setStyleSheet(sheet)
        self.zm.setToolTip("Select zoom tool")
        li = self.scene.addWidget(self.zm)
        li.setPos(-40, 15)

        self.dlt = QPushButton(key("delete"))
        self.dlt.setStyleSheet(sheet)
        self.dlt.setToolTip("Select delete tool")
        li = self.scene.addWidget(self.dlt)
        li.setPos(-40, 220)


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
