# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt, QLineF
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsLineItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem


class CommandLine(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, pti, ptf):
        super(CommandLine, self).__init__()
        self.scene = scene
        self.pti = pti
        self.ptf = ptf
        # A line from pti(nitial) to ptf(inal)
        self.lineItem = LineItemObject(self.pti, self.ptf)
        self.setText("Line")

    def redo(self):
        self.lineItem.flash_redo()
        self.scene.addItem(self.lineItem.li)

    def undo(self):
        self.lineItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.lineItem.li))


class LineItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pti, ptf):
        super(LineItemObject, self).__init__()
        self.li = LineItem(pti, ptf, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.li.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.li.setPen(QPen(Qt.red, value))


class LineItem(QGraphicsLineItem):
    # Very similar to the arrowitem, but no arrowhead
    def __init__(self, pti, ptf, parent=None):
        super(LineItem, self).__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.pti = pti
        self.ptf = ptf
        self.setLine(QLineF(self.pti, self.ptf))
        self.setPen(QPen(Qt.red, 2))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsLineItem.itemChange(self, change, value)

    def pickle(self):
        return [
            "Line",
            self.pti.x() + self.x(),
            self.pti.y() + self.y(),
            self.ptf.x() + self.x(),
            self.ptf.y() + self.y(),
        ]

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(
            self.scene().underImage, mode=Qt.ContainsItemShape
        ):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        super(LineItem, self).paint(painter, option, widget)
