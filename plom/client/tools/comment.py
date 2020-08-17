# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import QUndoCommand, QGraphicsItemGroup, QGraphicsItem

from plom.client.tools.delta import DeltaItem, GhostDelta
from plom.client.tools.move import *
from plom.client.tools.text import GhostText


class CommandGDT(QUndoCommand):
    # GDT = group of delta and text
    # Command to do a delta and a textitem (ie a standard comment)
    # Must change mark
    def __init__(self, scene, pt, delta, blurb, fontsize):
        super(CommandGDT, self).__init__()
        self.scene = scene
        self.pt = pt
        self.delta = delta
        self.blurb = blurb
        self.gdt = GroupDTItem(self.pt, self.delta, self.blurb, fontsize)
        self.setText("GroupDeltaText")

    def redo(self):
        # Mark increased by delta
        self.scene.changeTheMark(self.delta, undo=False)
        self.scene.addItem(self.gdt)
        self.gdt.blurb.flash_redo()
        self.gdt.di.flash_redo()

    def undo(self):
        # Mark decreased by delta - handled by undo flag
        self.scene.changeTheMark(self.delta, undo=True)
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.gdt))
        self.gdt.blurb.flash_undo()
        self.gdt.di.flash_undo()


class GroupDTItem(QGraphicsItemGroup):
    def __init__(self, pt, delta, blurb, fontsize):
        super(GroupDTItem, self).__init__()
        self.pt = pt
        self.di = DeltaItem(
            self.pt, delta, fontsize
        )  # positioned so centre under click
        self.blurb = blurb  # is a textitem already
        self.blurb.setTextInteractionFlags(Qt.NoTextInteraction)
        # Set the underlying delta and text to not pickle - since the GDTI will handle that
        self.saveable = True
        self.di.saveable = False
        self.blurb.saveable = False

        # check if needs tex->latex
        self.blurb.textToPng()

        # move blurb so that its top-left corner is next to top-right corner of delta.
        self.tweakPositions(delta)

        # set up animators for delete
        self.animator = [self.di, self.blurb]
        self.animateFlag = False
        self.thick = 1

        self.addToGroup(self.di)
        self.addToGroup(self.blurb)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def tweakPositions(self, dlt):
        pt = self.di.pos()
        self.blurb.setPos(pt)
        self.di.setPos(pt)
        if dlt != ".":
            cr = self.di.boundingRect()
            self.blurb.moveBy(cr.width() + 5, 0)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            command = CommandMoveItem(self, value)
            self.scene().undoStack.push(command)
        return QGraphicsItemGroup.itemChange(self, change, value)

    def pickle(self):
        return [
            "GroupDeltaText",
            self.pt.x() + self.x(),
            self.pt.y() + self.y(),
            self.di.delta,
            self.blurb.contents,
        ]

    def paint(self, painter, option, widget):
        if not self.collidesWithItem(
            self.scene().underImage, mode=Qt.ContainsItemShape
        ):
            painter.setPen(QPen(QColor(255, 165, 0), 4))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        else:
            # paint a bounding rectangle for undo/redo highlighting
            painter.setPen(QPen(QColor(255, 0, 0), self.thick, style=Qt.DotLine))
            painter.drawRoundedRect(option.rect, 10, 10)
            pass
        super(GroupDTItem, self).paint(painter, option, widget)


class GhostComment(QGraphicsItemGroup):
    def __init__(self, dlt, txt, fontsize):
        super(GhostComment, self).__init__()
        self.di = GhostDelta(dlt, fontsize)
        self.blurb = GhostText(txt, fontsize)
        self.changeComment(dlt, txt)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def tweakPositions(self, dlt, txt):
        pt = self.pos()
        self.blurb.setPos(pt)
        self.di.setPos(pt)
        if dlt == ".":
            cr = self.blurb.boundingRect()
            self.blurb.moveBy(0, -cr.height() / 2)
        else:
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
            # check if blurb is empty, move accordingly to hide it
            if txt == "":
                self.blurb.moveBy(0, -cr.height() / 2)
            else:
                self.blurb.moveBy(cr.width() + 5, -cr.height() / 2)

    def changeComment(self, dlt, txt):
        # need to force a bounding-rect update by removing an item and adding it back
        self.removeFromGroup(self.di)
        self.removeFromGroup(self.blurb)
        # change things
        self.di.changeDelta(dlt)
        self.blurb.changeText(txt)
        # move to correct positions
        self.tweakPositions(dlt, txt)
        self.addToGroup(self.blurb)
        if dlt == ".":
            self.di.setVisible(False)
        else:
            self.di.setVisible(True)
            self.addToGroup(self.di)

    def paint(self, painter, option, widget):
        # paint a bounding rectangle for undo/redo highlighting
        painter.setPen(QPen(Qt.blue, 0.5, style=Qt.DotLine))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super(GhostComment, self).paint(painter, option, widget)
