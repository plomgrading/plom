# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPen, QColor, QBrush
from PyQt5.QtWidgets import QGraphicsTextItem, QGraphicsItem

from plom.client.tools.text import UndoStackMoveTextMixin


class DeltaItem(UndoStackMoveTextMixin, QGraphicsTextItem):
    def __init__(self, pt, value, display_delta, style, fontsize=10):
        super().__init__()
        self.saveable = True
        self.display_delta = display_delta
        self.value = value
        self.restyle(style)
        self.setPlainText(" {} ".format(self.display_delta))
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

    def _pickle(self):
        # TODO: I don't think these are pickled directly anymore (?)
        return [
            "Delta",
            self.value,
            self.display_delta,
            self.scenePos().x(),
            self.scenePos().y() - self.offset,
        ]


class GhostDelta(QGraphicsTextItem):
    def __init__(self, display_delta, fontsize, *, legal=True):
        super().__init__()
        self.display_delta = display_delta
        if legal:
            self.setDefaultTextColor(Qt.blue)
        else:
            self.setDefaultTextColor(Qt.lightGray)

        self.setPlainText(" {} ".format(self.display_delta))
        font = QFont("Helvetica")
        # Slightly larger font than regular textitem.
        font.setPixelSize(round(1.25 * fontsize))
        self.setFont(font)
        # Is not editable.
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def changeDelta(self, display_delta, legal):
        self.display_delta = display_delta
        self.setPlainText(" {} ".format(self.display_delta))
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
