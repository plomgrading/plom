# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPen, QPainterPath, QColor, QBrush
from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsItem

from plom.client.tools import CommandTool, DeleteObject, UndoStackMoveMixin


class CommandQMark(CommandTool):
    def __init__(self, scene, pt):
        super().__init__(scene)
        self.obj = QMarkItem(pt, scene.style)
        self.do = DeleteObject(self.obj.shape())
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
        self.restyle(style)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.normal_thick = 3 * style["pen_width"] / 2
        self.setPen(QPen(style["annot_color"], self.normal_thick))

    def pickle(self):
        return ["QMark", self.pt.x() + self.x(), self.pt.y() + self.y()]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
