# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt, QLineF, QPointF
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsLineItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem


class CommandLine(QUndoCommand):
    def __init__(self, scene, pti, ptf):
        super().__init__()
        self.scene = scene
        # A line from pti(nitial) to ptf(inal)
        self.lineItem = LineItemObject(pti, ptf, scene.style)
        self.setText("Line")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Reconstruct from a serialized form."""
        assert cls.__name__.endswith(X[0]), 'Type "{}" mismatch: "{}"'.format(X[0], cls)
        X = X[1:]
        if len(X) != 4:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QPointF(X[0], X[1]), QPointF(X[2], X[3]))

    def redo(self):
        """Item knows how to highlight on undo and redo."""
        self.lineItem.flash_redo()
        self.scene.addItem(self.lineItem.item)

    def undo(self):
        """Undo animation takes 0.5s, so trigger removal after 0.5s."""
        self.lineItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.lineItem.item))


class LineItemObject(QGraphicsObject):
    """An object wrapper around LineItem (or subclass) to handle animation."""

    def __init__(self, pti, ptf, style):
        super().__init__()
        self.item = LineItem(pti, ptf, style=style, parent=self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        """Undo animation: thin -> thick -> none."""
        t = self.item.normal_thick
        self.anim.setDuration(200)
        self.anim.setStartValue(t)
        self.anim.setKeyValueAt(0.5, 3 * t)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        """Redo animation: thin -> med -> thin."""
        t = self.item.normal_thick
        self.anim.setDuration(200)
        self.anim.setStartValue(t)
        self.anim.setKeyValueAt(0.5, 2 * t)
        self.anim.setEndValue(t)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.item.pen().width()

    @thickness.setter
    def thickness(self, value):
        pen = self.item.pen()
        pen.setWidthF(value)
        self.item.setPen(pen)


class LineItem(QGraphicsLineItem):
    def __init__(self, pti, ptf, style, parent=None):
        super().__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.pti = pti
        self.ptf = ptf
        self.setLine(QLineF(self.pti, self.ptf))
        self.restyle(style)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.normal_thick = style["pen_width"]
        self.setPen(QPen(style["annot_color"], style["pen_width"]))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # If the position changes then do so with an redo/undo command
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)

    def pickle(self):
        return [
            self.__class__.__name__.replace("Item", ""),  # i.e., "Line",
            self.pti.x() + self.x(),
            self.pti.y() + self.y(),
            self.ptf.x() + self.x(),
            self.ptf.y() + self.y(),
        ]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        super().paint(painter, option, widget)
