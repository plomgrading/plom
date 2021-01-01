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

from plom.client.tools.line import CommandLine, LineItemObject, LineItem
from plom.client.tools.move import CommandMoveItem


class CommandArrow(CommandLine):
    def __init__(self, scene, pti, ptf):
        super(CommandLine, self).__init__()
        self.scene = scene
        # line starts at pti(nitial) and ends at ptf(inal).
        self.pti = pti
        self.ptf = ptf
        self.lineItem = ArrowItemObject(self.pti, self.ptf, scene.style)
        self.setText("Arrow")


class ArrowItemObject(LineItemObject):
    def __init__(self, pti, ptf, style):
        # TODO: use a ABC here?
        super(LineItemObject, self).__init__()
        self.li = ArrowItem(pti, ptf, style=style, parent=self)
        self.anim = QPropertyAnimation(self, b"thickness")


# TODO: LineItem is a QGraphicsLineItem, so cannot inherit (?)
class ArrowItem(QGraphicsPathItem):
    def __init__(self, pti, ptf, style, parent=None):
        """Creates an arrow from pti to ptf.
        Some manipulations required to draw the arrow head.
        """
        super().__init__()
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
        self.setPen(
            QPen(
                style["annot_color"],
                style["pen_width"],
                cap=Qt.RoundCap,
                join=Qt.RoundJoin,
            )
        )
        # fill in the arrowhead
        self.setBrush(QBrush(style["annot_color"]))
        # The line is moveable and should signal any changes
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            # If the position changes then do so with an redo/undo command
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)

    # poorman's inheritance!
    pickle = LineItem.pickle

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)


class CommandArrowDouble(CommandLine):
    def __init__(self, scene, pti, ptf):
        super(CommandLine, self).__init__()
        self.scene = scene
        # line starts at pti(nitial) and ends at ptf(inal).
        self.pti = pti
        self.ptf = ptf
        self.lineItem = ArrowDoubleItemObject(self.pti, self.ptf, scene.style)
        self.setText("ArrowDouble")


class ArrowDoubleItemObject(LineItemObject):
    # An object wrapper around the arrowitem to handle the
    # animation of its thickness
    def __init__(self, pti, ptf, style):
        super(LineItemObject, self).__init__()
        self.li = ArrowDoubleItem(pti, ptf, style=style, parent=self)
        self.anim = QPropertyAnimation(self, b"thickness")


class ArrowDoubleItem(QGraphicsPathItem):
    def __init__(self, pti, ptf, style, parent=None):
        """Creates an double-headed arrow from pti to ptf.
        Some manipulations required to draw the arrow head.
        """
        super().__init__()
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
        self.setPen(
            QPen(
                style["annot_color"],
                style["pen_width"],
                cap=Qt.RoundCap,
                join=Qt.RoundJoin,
            )
        )
        # fill in the arrowheads
        self.setBrush(QBrush(style["annot_color"]))
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
