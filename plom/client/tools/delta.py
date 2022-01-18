# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPen, QColor, QBrush
from PyQt5.QtWidgets import QGraphicsTextItem, QGraphicsItem

from plom.client.tools.text import CommandMoveText


class DeltaItem(QGraphicsTextItem):
    def __init__(self, pt, delta, style, fontsize=10):
        super().__init__()
        self.saveable = True
        self.delta = delta
        self.restyle(style)
        self.setPlainText(" {} ".format(self.delta))
        font = QFont("Helvetica")
        # Slightly larger font than regular textitem.
        font.setPixelSize(round(1.25 * fontsize))
        self.setFont(font)
        # Is not editable.
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        # centre under the mouse-click.
        self.setPos(pt)
        cr = self.boundingRect()
        self.offset = -cr.height() / 2
        self.moveBy(0, self.offset)

    def restyle(self, style):
        self.normal_thick = style["pen_width"]
        self.thick = self.normal_thick
        self.setDefaultTextColor(style["annot_color"])

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            if self.group() is None:  # make sure not part of a GDT
                painter.setPen(QPen(QColor(255, 165, 0), 4))
                painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
                painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
                painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
                painter.drawRoundedRect(option.rect, 10, 10)
        else:
            # paint the background
            painter.setPen(QPen(self.defaultTextColor(), self.thick))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super().paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveText(self, value)
            self.scene().undoStack.push(command)
        return super().itemChange(change, value)

    def pickle(self):
        return [
            "Delta",
            self.delta,
            self.scenePos().x(),
            self.scenePos().y() - self.offset,
        ]


class GhostDelta(QGraphicsTextItem):
    def __init__(self, delta, fontsize=10, legal=True):
        super().__init__()
        self.delta = delta
        if legal:
            self.setDefaultTextColor(Qt.blue)
        else:
            self.setDefaultTextColor(Qt.lightGray)

        self.setPlainText(" {} ".format(self.delta))
        font = QFont("Helvetica")
        # Slightly larger font than regular textitem.
        font.setPixelSize(round(1.25 * fontsize))
        self.setFont(font)
        # Is not editable.
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def changeDelta(self, dlt, legal=True):
        self.delta = dlt
        self.setPlainText(" {} ".format(self.delta))
        if legal:
            self.setDefaultTextColor(Qt.blue)
        else:
            self.setDefaultTextColor(Qt.lightGray)

    def paint(self, painter, option, widget):
        # paint the background
        painter.setPen(QPen(Qt.blue, 1))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super().paint(painter, option, widget)
