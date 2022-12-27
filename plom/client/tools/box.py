# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem

from plom.client.tools import CommandTool, DeleteObject, UndoStackMoveMixin


class CommandBox(CommandTool):
    def __init__(self, scene, rect):
        super().__init__(scene)
        self.obj = BoxItem(rect, scene.style)
        self.do = DeleteObject(self.obj.shape(), fill=True)
        self.setText("Box")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandBox from a serialized form."""
        assert X[0] == "Box"
        X = X[1:]
        if len(X) != 4:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QRectF(X[0], X[1], X[2], X[3]))


class BoxItem(UndoStackMoveMixin, QGraphicsRectItem):
    def __init__(self, rect, style):
        super().__init__()
        self.saveable = True
        self.setRect(rect)  # don't overwrite native rect function
        self.restyle(style)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.normal_thick = style["pen_width"]
        self.setPen(QPen(style["annot_color"], style["pen_width"]))
        self.setBrush(QBrush(style["box_tint"]))

    def pickle(self):
        return [
            "Box",
            self.rect().left() + self.x(),
            self.rect().top() + self.y(),
            self.rect().width(),
            self.rect().height(),
        ]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
