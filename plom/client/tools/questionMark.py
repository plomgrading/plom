# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPen, QPainterPath
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem

from plom.client.tools import OutOfBoundsPen, OutOfBoundsFill
from plom.client.tools import CommandTool, UndoStackMoveMixin


class CommandQMark(CommandTool):
    def __init__(self, scene, pt):
        super().__init__(scene)
        self.obj = QMarkItem(pt, scene.style)
        self.setText("QMark")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandQMark from a serialized form."""
        assert X[0] == "QMark"
        X = X[1:]
        if len(X) != 2:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QPointF(X[0], X[1]))


class QMarkItem(UndoStackMoveMixin, QGraphicsPathItem):
    def __init__(self, pt, style):
        super().__init__()
        self.saveable = True
        self.pt = pt
        self.path = QPainterPath()
        self.style = style
        # Draw a ?-mark with barycentre under mouseclick

        self.path.moveTo(pt.x() - self._scaler(6), pt.y() - self._scaler(10))
        self.path.quadTo(
            pt.x() - self._scaler(6),
            pt.y() - self._scaler(15),
            pt.x(),
            pt.y() - self._scaler(15),
        )
        self.path.quadTo(
            pt.x() + self._scaler(6),
            pt.y() - self._scaler(15),
            pt.x() + self._scaler(6),
            pt.y() - self._scaler(10),
        )
        self.path.cubicTo(
            pt.x() + self._scaler(6),
            pt.y() - self._scaler(1),
            pt.x(),
            pt.y() - self._scaler(7),
            pt.x(),
            pt.y() + self._scaler(2),
        )
        self.path.moveTo(pt.x(), pt.y() + self._scaler(12))
        self.path.lineTo(pt.x(), pt.y() + self._scaler(10))
        self.setPath(self.path)
        self.restyle(style)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def _scaler(self, num: float) -> float:
        """Scale a number based on global scene's scale.

        Args:
            num: the number to be scaled

        Returns:
            the scaled number.
        """
        return self.style["scale"] * num

    def restyle(self, style):
        self.normal_thick = 3 * style["pen_width"] / 2
        self.setPen(QPen(style["annot_color"], self.normal_thick))

    def pickle(self):
        return ["QMark", self.pt.x() + self.x(), self.pt.y() + self.y()]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(OutOfBoundsPen)
            painter.setBrush(OutOfBoundsFill)
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
