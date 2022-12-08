# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsItem

from plom.client.tools.pen import CommandPen, PenItem
from plom.client.tools import DeleteObject, UndoStackMoveMixin


class CommandHighlight(CommandPen):
    def __init__(self, scene, path):
        super().__init__(scene, path)
        self.obj = HighlightItem(path, scene.style)
        self.do = DeleteObject(self.obj.path)
        self.setText("Highlight")


class HighlightItem(UndoStackMoveMixin, QGraphicsPathItem):
    def __init__(self, path, style):
        super().__init__()
        self.saveable = True
        self.path = path
        self.setPath(self.path)
        self.restyle(style)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.setPen(QPen(style["highlight_color"], style["highlight_width"]))

    # poorman's inheritance!
    pickle = PenItem.pickle

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
