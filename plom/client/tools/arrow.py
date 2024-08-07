# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from math import sqrt

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QPainterPath, QBrush
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem

from plom.client.tools import OutOfBoundsPen, OutOfBoundsFill
from plom.client.tools.line import CommandLine, LineItem
from plom.client.tools import UndoStackMoveMixin


class CommandArrow(CommandLine):
    def __init__(self, scene, pti, ptf):
        super().__init__(scene, pti, ptf)
        # line starts at pti(nitial) and ends at ptf(inal).
        self.obj = ArrowItem(pti, ptf, scene.style)
        self.setText("Arrow")


# TODO: LineItem is a QGraphicsLineItem, so cannot inherit (?)
class ArrowItem(UndoStackMoveMixin, QGraphicsPathItem):
    def __init__(self, pti, ptf, style):
        """Creates an arrow from pti to ptf.

        Some manipulations required to draw the arrow head.
        """
        super().__init__()
        self.saveable = True
        self.ptf = ptf
        self.pti = pti
        path = self._make_path(pti, ptf)
        self._original_path = path
        self.setPath(path)
        self.restyle(style)

        # The line is moveable and should signal any changes
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.normal_thick = style["pen_width"]
        self.setPen(
            QPen(
                style["annot_color"],
                style["pen_width"],
                cap=Qt.PenCapStyle.RoundCap,
                join=Qt.PenJoinStyle.RoundJoin,
            )
        )
        self.setBrush(QBrush(style["annot_color"]))

    def _make_path(self, pti, ptf):
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
        # left-barb of the arrowhead
        self.arLeft = self.arBase - 10 * northog - 4 * ndelta
        # right-barb of the arrowhead
        self.arRight = self.arBase + 10 * northog - 4 * ndelta
        self.path = QPainterPath()
        # put a small ball at start of arrow.
        self.path.addEllipse(pti.x() - 6, pti.y() - 6, 12, 12)
        # draw line from pti to ptf
        self.path.moveTo(pti)
        self.path.lineTo(ptf)
        # line to left-barb then to base of arrowhead, then to right barb
        self.path.lineTo(self.arLeft)
        self.path.lineTo(self.arBase)
        self.path.lineTo(self.arRight)
        # then back to the end of the line.
        self.path.lineTo(ptf)
        return self.path

    # poorman's inheritance!
    pickle = LineItem.pickle

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(OutOfBoundsPen)
            painter.setBrush(OutOfBoundsFill)
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)


class CommandArrowDouble(CommandLine):
    def __init__(self, scene, pti, ptf):
        super().__init__(scene, pti, ptf)
        self.scene = scene
        # line starts at pti(nitial) and ends at ptf(inal).
        self.obj = ArrowDoubleItem(pti, ptf, scene.style)
        self.setText("ArrowDouble")


class ArrowDoubleItem(ArrowItem):
    def _make_path(self, pti, ptf):
        path = QPainterPath()
        # Some vectors:
        delta = ptf - pti
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        ndelta = delta / el
        northog = QPointF(-ndelta.y(), ndelta.x())
        # build arrow
        arBase = pti + 16 * ndelta
        arLeft = arBase + 10 * northog + 4 * ndelta
        arRight = arBase - 10 * northog + 4 * ndelta
        # draw first arrow.
        path.moveTo(pti)
        path.lineTo(arLeft)
        path.lineTo(arBase)
        path.lineTo(arRight)
        path.lineTo(pti)
        # draw line from pti to ptf
        path.lineTo(ptf)
        # other arrowhead
        arBase = ptf - 16 * ndelta
        arLeft = arBase - 10 * northog - 4 * ndelta
        arRight = arBase + 10 * northog - 4 * ndelta
        # line to left-barb then to base of arrowhead, then to right barb
        path.lineTo(arLeft)
        path.lineTo(arBase)
        path.lineTo(arRight)
        # then back to the end of the line.
        path.lineTo(ptf)
        return path
