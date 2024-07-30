# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPen, QPainterPath
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem

from plom.client.tools import OutOfBoundsPen, OutOfBoundsFill
from plom.client.tools import CommandTool, UndoStackMoveMixin
from plom.client.tools import DefaultTickRadius


class CommandTick(CommandTool):
    def __init__(self, scene, pt):
        super().__init__(scene)
        self.obj = TickItem(pt, scene.style)
        self.setText("Tick")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandTick from a serialized form."""
        assert X[0] == "Tick"
        X = X[1:]
        if len(X) != 2:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QPointF(X[0], X[1]))


class TickItem(UndoStackMoveMixin, QGraphicsPathItem):
    def __init__(self, pt, style):
        super().__init__()
        tick_radius = style["scale"] * DefaultTickRadius
        self.saveable = True
        self.pt = pt
        path = QPainterPath()
        # Draw the checkmark with barycentre under mouseclick.
        path.moveTo(pt.x() - tick_radius / 2, pt.y() - tick_radius / 2)
        path.lineTo(pt.x(), pt.y())
        path.lineTo(pt.x() + tick_radius, pt.y() - tick_radius)
        self.setPath(path)
        self.restyle(style)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.normal_thick = 3 * style["pen_width"] / 2
        self.setPen(QPen(style["annot_color"], self.normal_thick))

    def pickle(self):
        return ["Tick", self.pt.x() + self.x(), self.pt.y() + self.y()]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(OutOfBoundsPen)
            painter.setBrush(OutOfBoundsFill)
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
