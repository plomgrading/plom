# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, Qt, QPointF
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import QUndoCommand, QGraphicsItemGroup, QGraphicsItem

from plom.client.tools.delta import DeltaItem, GhostDelta
from plom.client.tools.move import CommandMoveItem
from plom.client.tools.text import GhostText, TextItem


class CommandGroupDeltaText(QUndoCommand):
    """A group of delta and text.

    Command to do a delta and a textitem together (a "rubric" or
    "saved comment").

    Note: must change mark
    """

    def __init__(self, scene, pt, delta, text):
        super().__init__()
        self.scene = scene
        self.gdt = GroupDeltaTextItem(
            pt, delta, text, scene, style=scene.style, fontsize=scene.fontSize
        )
        self.setText("GroupDeltaText")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandGroupDeltaText from a serialized GroupDeltaTextItem.

        TODO: could this comandFoo.__init__() take a FooItem?
        """
        assert X[0] == "GroupDeltaText"
        X = X[1:]
        if len(X) != 4:
            raise ValueError("wrong length of pickle data")
        # knows to latex it if needed.
        return cls(scene, QPointF(X[0], X[1]), X[2], X[3])

    def redo(self):
        # Mark increased by delta
        self.scene.changeTheMark(self.gdt.di.delta, undo=False)
        self.scene.addItem(self.gdt)
        self.gdt.blurb.flash_redo()
        self.gdt.di.flash_redo()

    def undo(self):
        # Mark decreased by delta - handled by undo flag
        self.scene.changeTheMark(self.gdt.di.delta, undo=True)
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.gdt))
        self.gdt.blurb.flash_undo()
        self.gdt.di.flash_undo()


class GroupDeltaTextItem(QGraphicsItemGroup):
    """A group of Delta and Text presenting a rubric.

    TODO: passing in scene is a workaround so the TextItem can talk to
    someone about building LaTeX... can we refactor that somehow?
    """

    def __init__(self, pt, delta, text, scene, style, fontsize):
        super().__init__()
        self.pt = pt
        self.style = style
        # centre under click
        self.di = DeltaItem(pt, delta, style=style, fontsize=fontsize)
        self.blurb = TextItem(
            pt, text, scene, fontsize=fontsize, color=style["annot_color"]
        )
        # set style
        self.restyle(style)
        # Set the underlying delta and text to not pickle - since the GDTI will handle that
        self.saveable = True
        self.di.saveable = False
        self.blurb.saveable = False

        # TODO: the blurb will do this anyway, but may defer this to "later",
        # meanwhile we have tqhe wrong size for tweakPositions (Issue #1391).
        # TODO: can be removed once the border adjusts automatically to resize.
        self.blurb.textToPng()

        # move blurb so that its top-left corner is next to top-right corner of delta.
        self.tweakPositions(delta)

        # set up animators for delete
        self.animator = [self.di, self.blurb]
        self.animateFlag = False

        self.addToGroup(self.di)
        self.addToGroup(self.blurb)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.style = style
        self.thick = self.style["pen_width"] / 2
        # force a relatexing of the textitem in case it is a latex png
        self.blurb.restyle(style)
        self.di.restyle(style)

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
            self.blurb.getContents(),
        ]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            painter.setPen(QPen(QColor(255, 165, 0), 4))
            painter.setBrush(QBrush(QColor(255, 165, 0, 128)))
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        else:
            # paint a bounding rectangle for undo/redo highlighting
            painter.setPen(
                QPen(self.style["annot_color"], self.thick, style=Qt.DotLine)
            )
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)


class GhostComment(QGraphicsItemGroup):
    def __init__(self, dlt, txt, fontsize):
        super().__init__()
        self.di = GhostDelta(dlt, fontsize)
        self.blurb = GhostText(txt, fontsize)
        self.changeComment(dlt, txt)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def tweakPositions(self):
        """Adjust the positions of the delta and text depending on their size and ontent."""
        pt = self.pos()
        self.blurb.setPos(pt)
        self.di.setPos(pt)
        if self.di.delta == ".":
            cr = self.blurb.boundingRect()
            self.blurb.moveBy(0, -cr.height() / 2)
        else:
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
            # check if blurb is empty, move accordingly to hide it
            if not self.blurb.is_rendered() and self.blurb.toPlainText() == "":
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
        self.tweakPositions()
        self.addToGroup(self.blurb)
        if dlt == ".":
            self.di.setVisible(False)
        else:
            self.di.setVisible(True)
            self.addToGroup(self.di)

    def paint(self, painter, option, widget):
        # paint a bounding rectangle for undo/redo highlighting
        # TODO: pen width hardcoded
        painter.setPen(QPen(Qt.blue, 0.5, style=Qt.DotLine))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
