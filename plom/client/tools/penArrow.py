# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from math import sqrt

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPen, QPainterPath, QBrush, QColor
from PyQt5.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsPathItem,
    QGraphicsItem,
)

from plom.client.tools import UndoStackMoveMixin
from plom.client.tools.pen import CommandPen, PenItem


class CommandPenArrow(CommandPen):
    def __init__(self, scene, path):
        super().__init__(scene, path)
        self.obj = PenArrowItem(path, scene.style)
        self.setText("PenArrow")


class PenArrowItem(UndoStackMoveMixin, QGraphicsItemGroup):
    def __init__(self, path, style):
        super().__init__()
        self.saveable = True
        self.pi = QGraphicsPathItem()
        self.path = path

        # set arrowhead initial
        e0 = self.path.elementAt(0)
        e1 = self.path.elementAt(1)
        pti = QPointF(e1.x, e1.y)
        ptf = QPointF(e0.x, e0.y)
        delta = ptf - pti
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        ndelta = delta / el
        northog = QPointF(-ndelta.y(), ndelta.x())
        arBase = ptf - 16 * ndelta
        arTip = ptf + 8 * ndelta
        arLeft = arBase - 10 * northog - 4 * ndelta
        arRight = arBase + 10 * northog - 4 * ndelta
        self.ari = QPainterPath()
        self.ari.moveTo(ptf)
        self.ari.lineTo(arLeft)
        self.ari.lineTo(arBase)
        self.ari.lineTo(arRight)
        self.ari.lineTo(ptf)
        self.endi = QGraphicsPathItem()
        self.endi.setPath(self.ari)
        # set arrowhead final
        e2 = self.path.elementAt(self.path.elementCount() - 2)
        e3 = self.path.elementAt(self.path.elementCount() - 1)
        pti = QPointF(e2.x, e2.y)
        ptf = QPointF(e3.x, e3.y)
        delta = ptf - pti
        el = sqrt(delta.x() ** 2 + delta.y() ** 2)
        ndelta = delta / el
        northog = QPointF(-ndelta.y(), ndelta.x())
        arBase = ptf - 16 * ndelta
        arTip = ptf + 8 * ndelta
        arLeft = arBase - 10 * northog - 4 * ndelta
        arRight = arBase + 10 * northog - 4 * ndelta
        self.arf = QPainterPath()
        self.arf.moveTo(ptf)
        self.arf.lineTo(arLeft)
        self.arf.lineTo(arBase)
        self.arf.lineTo(arRight)
        self.arf.lineTo(ptf)
        self.endf = QGraphicsPathItem()
        self.endf.setPath(self.arf)
        # put everything together
        self.pi.setPath(self.path)
        self.restyle(style)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.addToGroup(self.pi)
        self.addToGroup(self.endi)
        self.addToGroup(self.endf)

    def restyle(self, style):
        self.normal_thick = style["pen_width"]
        self.pi.setPen(QPen(style["annot_color"], style["pen_width"]))
        self.endi.setPen(QPen(style["annot_color"], style["pen_width"]))
        self.endf.setPen(QPen(style["annot_color"], style["pen_width"]))
        self.endi.setBrush(QBrush(style["annot_color"]))
        self.endf.setBrush(QBrush(style["annot_color"]))

    # poorman's inheritance!
    pickle = PenItem.pickle

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(QPen(QColor(255, 165, 0), 8))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
