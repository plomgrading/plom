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
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools.move import CommandMoveItem


class CommandArrow(QUndoCommand):
    # Command to create/remove an arrow object
    def __init__(self, scene, pti, ptf):
        super(CommandArrow, self).__init__()
        self.scene = scene
        # line starts at pti(nitial) and ends at ptf(inal).
        self.pti = pti
        self.ptf = ptf
        # create an arrow item
        self.arrowItem = ArrowItemObject(self.pti, self.ptf)
        self.setText("Arrow")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandArrow from a serialized form."""
        assert X[0] == "Arrow"
        X = X[1:]
        if len(X) != 4:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QPointF(X[0], X[1]), QPointF(X[2], X[3]))

    def redo(self):
        # arrow item knows how to highlight on undo and redo.
        self.arrowItem.flash_redo()
        self.scene.addItem(self.arrowItem.ai)

    def undo(self):
        # the undo animation takes 0.5s
        # so trigger its removal after 0.5s.
        self.arrowItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.arrowItem.ai))


class ArrowItemObject(QGraphicsObject):
    # An object wrapper around the arrowitem to handle the
    # animation of its thickness
    def __init__(self, pti, ptf):
        super(ArrowItemObject, self).__init__()
        self.ai = ArrowItem(pti, ptf, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        # thin -> thick -> none.
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # thin -> med -> thin.
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    # Set and get thickness of the pen to draw the arrow.
    @pyqtProperty(int)
    def thickness(self):
        return self.ai.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.ai.setPen(QPen(Qt.red, value))


class ArrowItem(QGraphicsPathItem):
    def __init__(self, pti, ptf, parent=None):
        """Creates an arrow from pti to ptf.
        Some manipulations required to draw the arrow head.
        """
        super(ArrowItem, self).__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.ptf = ptf
        self.pti = pti
        # vector direction of line
        delta = ptf - pti
        # length of the line
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        # unit vector in direction of line.
        ndelta = delta / el
        # orthogonal unit vector to line.
        northog = QPointF(-ndelta.y(), ndelta.x())
        # base of arrowhead
        self.arBase = ptf - 16 * ndelta
        # point of arrowhead
        self.arTip = ptf + 8 * ndelta
        # left-barb of the arrowhead
        self.arLeft = self.arBase - 10 * northog - 4 * ndelta
        # right-barb of the arrowhead
        self.arRight = self.arBase + 10 * northog - 4 * ndelta
        self.path = QPainterPath()
        # put a small ball at start of arrow.
        self.path.addEllipse(self.pti.x() - 6, self.pti.y() - 6, 12, 12)
        # draw line from pti to ptf
        self.path.moveTo(self.pti)
        self.path.lineTo(self.ptf)
        # line to left-barb then to base of arrowhead, then to right barb
        self.path.lineTo(self.arLeft)
        self.path.lineTo(self.arBase)
        self.path.lineTo(self.arRight)
        # then back to the end of the line.
        self.path.lineTo(self.ptf)
        self.setPath(self.path)
        # style the line.
        self.setPen(QPen(Qt.red, 2, cap=Qt.RoundCap, join=Qt.RoundJoin))
        # fill in the arrow with a red brush
        self.setBrush(QBrush(Qt.red))
        # The line is moveable and should signal any changes
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # If the position changes then do so with an redo/undo command
            command = CommandMoveItem(self, value)
            # Push the command onto the stack.
            self.scene().undoStack.push(command)
        # Exec the parent class change command.
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        return [
            "Arrow",
            self.pti.x() + self.x(),
            self.pti.y() + self.y(),
            self.ptf.x() + self.x(),
            self.ptf.y() + self.y(),
        ]

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(self.scene().underRect, mode=Qt.ContainsItemShape):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(ArrowItem, self).paint(painter, option, widget)


class CommandArrowDouble(QUndoCommand):
    # Command to create/remove an arrow object
    def __init__(self, scene, pti, ptf):
        super(CommandArrowDouble, self).__init__()
        self.scene = scene
        # line starts at pti(nitial) and ends at ptf(inal).
        self.pti = pti
        self.ptf = ptf
        # create an arrow item
        self.arrowItem = ArrowDoubleItemObject(self.pti, self.ptf)
        self.setText("ArrowDouble")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandArrowDouble from a serialized form."""
        assert X[0] == "ArrowDouble"
        X = X[1:]
        if len(X) != 4:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QPointF(X[0], X[1]), QPointF(X[2], X[3]))

    def redo(self):
        # arrow item knows how to highlight on undo and redo.
        self.arrowItem.flash_redo()
        self.scene.addItem(self.arrowItem.ai)

    def undo(self):
        # the undo animation takes 0.5s
        # so trigger its removal after 0.5s.
        self.arrowItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.arrowItem.ai))


class ArrowDoubleItemObject(QGraphicsObject):
    # An object wrapper around the arrowitem to handle the
    # animation of its thickness
    def __init__(self, pti, ptf):
        super(ArrowDoubleItemObject, self).__init__()
        self.ai = ArrowDoubleItem(pti, ptf, self)
        self.anim = QPropertyAnimation(self, b"thickness")

    def flash_undo(self):
        # thin -> thick -> none.
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 6)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # thin -> med -> thin.
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
        self.anim.start()

    # Set and get thickness of the pen to draw the arrow.
    @pyqtProperty(int)
    def thickness(self):
        return self.ai.pen().width()

    @thickness.setter
    def thickness(self, value):
        self.ai.setPen(QPen(Qt.red, value))


class ArrowDoubleItem(QGraphicsPathItem):
    def __init__(self, pti, ptf, parent=None):
        """Creates an double-headed arrow from pti to ptf.
        Some manipulations required to draw the arrow head.
        """
        super(ArrowDoubleItem, self).__init__()
        self.saveable = True
        self.animator = [parent]
        self.animateFlag = False
        self.ptf = ptf
        self.pti = pti
        self.path = QPainterPath()
        # Some vectors:
        delta = ptf - pti
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        ndelta = delta / el
        northog = QPointF(-ndelta.y(), ndelta.x())
        # build arrow
        arBase = pti + 16 * ndelta
        arTip = pti - 8 * ndelta
        arLeft = arBase + 10 * northog + 4 * ndelta
        arRight = arBase - 10 * northog + 4 * ndelta
        # draw first arrow.
        self.path.moveTo(self.pti)
        self.path.lineTo(arLeft)
        self.path.lineTo(arBase)
        self.path.lineTo(arRight)
        self.path.lineTo(self.pti)
        # draw line from pti to ptf
        self.path.lineTo(self.ptf)
        # other arrowhead
        arBase = ptf - 16 * ndelta
        arTip = ptf + 8 * ndelta
        arLeft = arBase - 10 * northog - 4 * ndelta
        arRight = arBase + 10 * northog - 4 * ndelta
        # line to left-barb then to base of arrowhead, then to right barb
        self.path.lineTo(arLeft)
        self.path.lineTo(arBase)
        self.path.lineTo(arRight)
        # then back to the end of the line.
        self.path.lineTo(self.ptf)
        self.setPath(self.path)
        # style the line.
        self.setPen(QPen(Qt.red, 2, cap=Qt.RoundCap, join=Qt.RoundJoin))
        # fill in the arrow with a red brush
        self.setBrush(QBrush(Qt.red))
        # The line is moveable and should signal any changes
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # If the position changes then do so with an redo/undo command
            command = CommandMoveItem(self, value)
            # Push the command onto the stack.
            self.scene().undoStack.push(command)
        # Exec the parent class change command.
        return QGraphicsPathItem.itemChange(self, change, value)

    def pickle(self):
        return [
            "ArrowDouble",
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
        # paint the normal item with the default 'paint' method
        super(ArrowDoubleItem, self).paint(painter, option, widget)
