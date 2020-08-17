# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, pyqtProperty
from PyQt5.QtGui import QFont, QPen, QColor, QBrush
from PyQt5.QtWidgets import QUndoCommand, QGraphicsTextItem, QGraphicsItem

from plom.client.tools.text import CommandMoveText


class CommandDelta(QUndoCommand):
    # Very similar to CommandArrow
    # But must send new mark to scene
    def __init__(self, scene, pt, delta, fontsize):
        super(CommandDelta, self).__init__()
        self.scene = scene
        self.pt = pt
        self.delta = delta
        self.delItem = DeltaItem(self.pt, self.delta, fontsize)
        self.setText("Delta")

    def redo(self):
        # Mark increased by delta
        self.scene.changeTheMark(self.delta, undo=False)
        self.delItem.flash_redo()
        self.scene.addItem(self.delItem)

    def undo(self):
        # Mark decreased by delta - handled by undo flag
        self.scene.changeTheMark(self.delta, undo=True)
        self.delItem.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.delItem))


class DeltaItem(QGraphicsTextItem):
    # Similar to textitem
    def __init__(self, pt, delta, fontsize=10):
        super(DeltaItem, self).__init__()
        self.saveable = True
        self.animator = [self]
        self.animateFlag = False
        self.thick = 2
        self.delta = delta
        self.setDefaultTextColor(Qt.red)
        self.setPlainText(" {} ".format(self.delta))
        self.font = QFont("Helvetica")
        # Slightly larger font than regular textitem.
        self.font.setPointSizeF(1.25 * fontsize)
        self.setFont(self.font)
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

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(
            self.scene().underImage, mode=Qt.ContainsItemShape
        ):
            if self.group() is None:
                painter.setPen(QPen(QColor(255, 165, 0), 4))
                painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
                painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
                painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
                painter.drawRoundedRect(option.rect, 10, 10)
        else:
            # paint the background
            painter.setPen(QPen(Qt.red, self.thick))
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal TextItem with the default 'paint' method
        super(DeltaItem, self).paint(painter, option, widget)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveText(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsTextItem.itemChange(self, change, value)

    def flash_undo(self):
        # Animate border when undo thin->thick->none
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 8)
        self.anim.setEndValue(0)
        self.anim.start()

    def flash_redo(self):
        # Animate border when undo thin->med->thin
        self.anim.setDuration(200)
        self.anim.setStartValue(2)
        self.anim.setKeyValueAt(0.5, 4)
        self.anim.setEndValue(2)
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
    # Similar to textitem
    def __init__(self, delta, fontsize=10):
        super(GhostDelta, self).__init__()
        self.delta = int(delta)
        self.setDefaultTextColor(Qt.blue)
        self.setPlainText(" {} ".format(self.delta))
        self.font = QFont("Helvetica")
        # Slightly larger font than regular textitem.
        self.font.setPointSizeF(1.25 * fontsize)
        self.setFont(self.font)
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
