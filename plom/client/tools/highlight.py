# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import (
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools.pen import CommandPen, PenItem
from plom.client.tools import CommandMoveItem


class CommandHighlight(CommandPen):
    def __init__(self, scene, path):
        super(CommandPen, self).__init__()
        self.scene = scene
        self.penobj = HighlightItemObject(path, scene.style)
        self.setText("Highlight")


class HighlightItemObject(QGraphicsObject):
    # As per the ArrowItemObject except animate the opacity of
    # the highlighter path
    def __init__(self, path, style):
        super(HighlightItemObject, self).__init__()
        self.item = HighlightItem(path, style=style, parent=self)
        self.anim = QPropertyAnimation(self, b"opacity")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(64)
        self.anim.setKeyValueAt(0.5, 192)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(64)
        self.anim.setKeyValueAt(0.5, 96)
        self.anim.setEndValue(64)
        self.anim.start()

    @pyqtProperty(int)
    def opacity(self):
        return self.item.pen().color().alpha()

    @opacity.setter
    def opacity(self, value):
        c = self.item.pen().color()
        w = self.item.pen().widthF()
        c.setAlpha(value)
        self.item.setPen(QPen(c, w))


class HighlightItem(QGraphicsPathItem):
    def __init__(self, path, style, parent=None):
        super().__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.path = path
        self.setPath(self.path)
        self.restyle(style)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.setPen(QPen(style["highlight_color"], style["highlight_width"]))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)

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
