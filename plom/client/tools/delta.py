# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, pyqtProperty, QPointF
from PyQt5.QtGui import QFont, QPen, QColor, QBrush
from PyQt5.QtWidgets import QUndoCommand, QGraphicsTextItem, QGraphicsItem

from plom.client.tools.text import CommandMoveText


class CommandDelta(QUndoCommand):
    """Handle the placing and undoing/redoing of Deltas.

    Very similar to CommandLine et al, but undo/redo
    must send new mark to scene.
    """

    def __init__(self, scene, pt, delta):
        super().__init__()
        self.scene = scene
        self.item = DeltaItem(pt, delta, style=scene.style, fontsize=scene.fontSize)
        self.setText("Delta")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandDelta from a serialized form."""
        assert X[0] == "Delta"
        X = X[1:]
        if len(X) != 3:
            raise ValueError("wrong length of pickle data")
        return cls(scene, QPointF(X[1], X[2]), X[0])

    def redo(self):
        # Mark increased by delta
        self.scene.changeTheMark(self.item.delta, undo=False)
        self.item.flash_redo()
        self.scene.addItem(self.item)

    def undo(self):
        # Mark decreased by delta - handled by undo flag
        self.scene.changeTheMark(self.item.delta, undo=True)
        self.item.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.item))


class DeltaItem(QGraphicsTextItem):
    def __init__(self, pt, delta, style, fontsize=10):
        super().__init__()
        self.saveable = True
        self.animator = [self]
        self.animateFlag = False
        self.delta = delta
        self.restyle(style)
        self.setPlainText(" {} ".format(self.delta))
        font = QFont("Helvetica")
        # Slightly larger font than regular textitem.
        font.setPointSizeF(1.25 * fontsize)
        self.setFont(font)
        # Is not editable.
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        # Has an animated border for undo/redo.
        self.anim = QPropertyAnimation(self, b"thickness")
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

    def flash_undo(self):
        # Animate border when undo thin->thick->none
        self.anim.setDuration(200)
        self.anim.setStartValue(self.normal_thick)
        self.anim.setKeyValueAt(0.5, 4 * self.normal_thick)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # Animate border when undo thin->med->thin
        self.anim.setDuration(200)
        self.anim.setStartValue(self.normal_thick)
        self.anim.setKeyValueAt(0.5, 2 * self.normal_thick)
        self.anim.setEndValue(self.normal_thick)
        self.anim.start()

    def pickle(self):
        return [
            "Delta",
            self.delta,
            self.scenePos().x(),
            self.scenePos().y() - self.offset,
        ]

    # For the animation of border
    @pyqtProperty(int)
    def thickness(self):
        return self.thick

    # For the animation of border
    @thickness.setter
    def thickness(self, value):
        self.thick = value
        self.update()


class GhostDelta(QGraphicsTextItem):
    def __init__(self, delta, fontsize=10):
        super().__init__()
        self.delta = delta
        self.setDefaultTextColor(Qt.blue)
        self.setPlainText(" {} ".format(self.delta))
        font = QFont("Helvetica")
        # Slightly larger font than regular textitem.
        font.setPointSizeF(1.25 * fontsize)
        self.setFont(font)
        # Is not editable.
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def changeDelta(self, dlt):
        self.delta = dlt
        self.setPlainText(" {} ".format(self.delta))

    def paint(self, painter, option, widget):
        # paint the background
        painter.setPen(QPen(Qt.blue, 1))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super(GhostDelta, self).paint(painter, option, widget)
