# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from math import sqrt

from PyQt5.QtCore import QTimer, QPropertyAnimation, pyqtProperty, Qt, QPointF
from PyQt5.QtGui import QPen, QPainterPath, QBrush, QColor
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsItemGroup,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem, log


class CommandPenArrow(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, path):
        super(CommandPenArrow, self).__init__()
        self.scene = scene
        self.path = path
        self.penItem = PenArrowItemObject(self.path)
        self.setText("PenArrow")

    def redo(self):
        self.penItem.flash_redo()
        self.scene.addItem(self.penItem.pi)

    def undo(self):
        self.penItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.penItem.pi))


class PenArrowItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, path):
        super(PenArrowItemObject, self).__init__()
        self.pi = PenArrowItem(path, self)
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
        return self.pi.pi.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.pi.pi.setPen(QPen(Qt.red, value))
        self.pi.endi.setPen(QPen(Qt.red, value))
        self.pi.endf.setPen(QPen(Qt.red, value))


class PenArrowItem(QGraphicsItemGroup):
    def __init__(self, path, parent=None):
        super(PenArrowItem, self).__init__()
        self.saveable = True
        self.pi = QGraphicsPathItem()
        self.path = path
        self.animator = [parent]
        self.animateFlag = False

        # set arrowhead initial
        e0 = self.path.elementAt(0)
        e1 = self.path.elementAt(1)
        pti = QPointF(e1.x, e1.y)
        ptf = QPointF(e0.x, e0.y)
        delta = ptf - pti
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        ndelta = delta / el
        northog = QPointF(-ndelta.y(), ndelta.x())
        arBase = ptf - 16 * ndelta
        arTip = ptf + 8 * ndelta
        arLeft = arBase - 10 * northog - 4 * ndelta
        arRight = arBase + 10 * northog - 4 * ndelta
        self.ari = QPainterPath()
        self.ari.moveTo(ptf)
        self.ari.lineTo(arLeft)
        self.ari.lineTo(arBase)
        self.ari.lineTo(arRight)
        self.ari.lineTo(ptf)
        self.endi = QGraphicsPathItem()
        self.endi.setPath(self.ari)
        # set arrowhead final
        e2 = self.path.elementAt(self.path.elementCount() - 2)
        e3 = self.path.elementAt(self.path.elementCount() - 1)
        pti = QPointF(e2.x, e2.y)
        ptf = QPointF(e3.x, e3.y)
        delta = ptf - pti
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        ndelta = delta / el
        northog = QPointF(-ndelta.y(), ndelta.x())
        arBase = ptf - 16 * ndelta
        arTip = ptf + 8 * ndelta
        arLeft = arBase - 10 * northog - 4 * ndelta
        arRight = arBase + 10 * northog - 4 * ndelta
        self.arf = QPainterPath()
        self.arf.moveTo(ptf)
        self.arf.lineTo(arLeft)
        self.arf.lineTo(arBase)
        self.arf.lineTo(arRight)
        self.arf.lineTo(ptf)
        self.endf = QGraphicsPathItem()
        self.endf.setPath(self.arf)
        # put everything together
        self.pi.setPath(self.path)
        self.pi.setPen(QPen(Qt.red, 2))
        self.endi.setPen(QPen(Qt.red, 2))
        self.endi.setBrush(QBrush(Qt.red))
        self.endf.setPen(QPen(Qt.red, 2))
        self.endf.setBrush(QBrush(Qt.red))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.addToGroup(self.pi)
        self.addToGroup(self.endi)
        self.addToGroup(self.endf)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsItemGroup.itemChange(self, change, value)

    def pickle(self):
        pth = []
        for k in range(self.path.elementCount()):
            # e should be either a moveTo or a lineTo
            e = self.path.elementAt(k)
            if e.isMoveTo():
                pth.append(["m", e.x + self.x(), e.y + self.y()])
            else:
                if e.isLineTo():
                    pth.append(["l", e.x + self.x(), e.y + self.y()])
                else:
                    log.error("Problem pickling penarrowitem path {}".format(self.path))
        return ["PenArrow", pth]

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(
            self.scene().underImage, mode=Qt.ContainsItemShape
        ):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(PenArrowItem, self).paint(painter, option, widget)
