# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPen, QBrush
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem

from plom.client.tools import OutOfBoundsPen, OutOfBoundsFill
from plom.client.tools import CommandTool, UndoStackMoveMixin


class CommandEllipse(CommandTool):
    def __init__(self, scene, rect):
        super().__init__(scene)
        self.obj = EllipseItem(rect, scene.style)
        self.setText("Ellipse")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandEllipse from a serialized form."""
        assert X[0] == "Ellipse"
        X = X[1:]
        if len(X) != 4:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QRectF(X[0], X[1], X[2], X[3]))


class EllipseItem(UndoStackMoveMixin, QGraphicsEllipseItem):
    def __init__(self, rect, style):
        super().__init__()
        self.saveable = True
        self.rect = rect
        self.setRect(self.rect)
        self.restyle(style)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.normal_thick = style["pen_width"]
        self.setPen(QPen(style["annot_color"], style["pen_width"]))
        self.setBrush(QBrush(style["box_tint"]))

    def pickle(self):
        return [
            "Ellipse",
            self.rect.left() + self.x(),
            self.rect.top() + self.y(),
            self.rect.width(),
            self.rect.height(),
        ]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(OutOfBoundsPen)
            painter.setBrush(OutOfBoundsFill)
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
