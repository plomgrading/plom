# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt6.QtGui import QPen, QPainterPath
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsItem

from plom.client.tools import OutOfBoundsPen, OutOfBoundsFill
from plom.client.tools.pen import CommandPen, PenItem
from plom.client.tools import UndoStackMoveMixin


class CommandHighlight(CommandPen):
    def __init__(self, scene, path):
        super().__init__(scene, path)
        self.obj = HighlightItem(path, scene.style)
        self.setText("Highlight")

    def get_undo_redo_animation_shape(self) -> QPainterPath:
        # Not entirely sure why this helps but the default shape() draws
        # unpleasant blue lines orthogonal to the path.
        return self.obj._original_path


class HighlightItem(UndoStackMoveMixin, QGraphicsPathItem):
    def __init__(self, path, style):
        super().__init__()
        self.saveable = True
        self._original_path = path
        self.setPath(path)
        self.restyle(style)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.setPen(QPen(style["highlight_color"], style["highlight_width"]))

    # poorman's inheritance!
    pickle = PenItem.pickle

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            # paint a bounding rectangle out-of-bounds warning
            painter.setPen(OutOfBoundsPen)
            painter.setBrush(OutOfBoundsFill)
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
