# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import Qt, QPointF, QTimer, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QPen, QPainterPath, QColor, QBrush
from PyQt5.QtWidgets import (
    QUndoCommand,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools import CommandMoveItem


class CommandQMark(QUndoCommand):
    # Very similar to CommandArrow
    def __init__(self, scene, pt):
        super(CommandQMark, self).__init__()
        self.scene = scene
        self.pt = pt
        self.qm = QMarkItemObject(self.pt)
        self.setText("QMark")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandQMark from a serialized form."""
        assert X[0] == "QMark"
        X = X[1:]
        if len(X) != 2:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QPointF(X[0], X[1]))

    def redo(self):
        self.qm.flash_redo()
        self.scene.addItem(self.qm.qmi)

    def undo(self):
        self.qm.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.qm.qmi))


class QMarkItemObject(QGraphicsObject):
    # As per the ArrowItemObject
    def __init__(self, pt):
        super(QMarkItemObject, self).__init__()
        self.qmi = QMarkItem(pt, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        self.anim.setDuration(200)
        self.anim.setStartValue(3)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(3)
        self.anim.start()

    @pyqtProperty(int)
    def thickness(self):
        return self.qmi.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.qmi.setPen(QPen(Qt.red, value))


class QMarkItem(QGraphicsPathItem):
    # Very similar to the arrowitem, but careful drawing the "?"
    def __init__(self, pt, parent=None):
        super(QMarkItem, self).__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.pt = pt
        self.path = QPainterPath()
        # Draw a ?-mark with barycentre under mouseclick
        self.path.moveTo(pt.x() - 6, pt.y() - 10)
        self.path.quadTo(pt.x() - 6, pt.y() - 15, pt.x(), pt.y() - 15)
        self.path.quadTo(pt.x() + 6, pt.y() - 15, pt.x() + 6, pt.y() - 10)
        self.path.cubicTo(
            pt.x() + 6, pt.y() - 1, pt.x(), pt.y() - 7, pt.x(), pt.y() + 2
        )
        self.path.moveTo(pt.x(), pt.y() + 12)
        self.path.lineTo(pt.x(), pt.y() + 10)
        self.setPath(self.path)
        self.setPen(QPen(Qt.red, 3))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        return ["QMark", self.pt.x() + self.x(), self.pt.y() + self.y()]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(QMarkItem, self).paint(painter, option, widget)
