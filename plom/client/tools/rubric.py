# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from PyQt5.QtCore import QTimer, Qt, QPointF
from PyQt5.QtGui import QPen, QColor, QBrush
from PyQt5.QtWidgets import QGraphicsItemGroup, QGraphicsItem

from plom.client.tools import CommandMoveItem, CommandTool, DeleteObject
from plom.client.tools.delta import DeltaItem, GhostDelta
from plom.client.tools.text import GhostText, TextItem


class CommandGroupDeltaText(CommandTool):
    """A group of delta and text.

    Command to do a delta and a textitem together (a "rubric" or
    "saved comment").

    Note: must change mark
    """

    def __init__(self, scene, pt, rid, kind, delta, text):
        super().__init__(scene)
        self.gdt = GroupDeltaTextItem(
            pt,
            delta,
            text,
            rid,
            kind,
            _scene=scene,
            style=scene.style,
            fontsize=scene.fontSize,
        )
        self.do = DeleteObject(self.gdt.shape(), fill=True)
        self.setText("GroupDeltaText")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandGroupDeltaText from a serialized GroupDeltaTextItem.

        TODO: could this comandFoo.__init__() take a FooItem?
        """
        assert X[0] == "GroupDeltaText"
        X = X[1:]
        if len(X) != 6:
            raise ValueError("wrong length of pickle data")
        # knows to latex it if needed.
        return cls(scene, QPointF(X[0], X[1]), X[2], X[3], X[4], X[5])

    def redo(self):
        self.scene.addItem(self.gdt)
        # animate
        self.scene.addItem(self.do.item)
        self.do.flash_redo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.do.item))
        #
        self.scene.refreshStateAndScore()

    def undo(self):
        self.scene.removeItem(self.gdt)
        # animate
        self.scene.addItem(self.do.item)
        self.do.flash_undo()
        QTimer.singleShot(200, lambda: self.scene.removeItem(self.do.item))
        #
        self.scene.refreshStateAndScore()


class GroupDeltaTextItem(QGraphicsItemGroup):
    """A group of Delta and Text presenting a rubric.

    TODO: passing in scene is a workaround so the TextItem can talk to
    someone about building LaTeX... can we refactor that somehow?
    """

    def __init__(self, pt, delta, text, rid, kind, *, _scene, style, fontsize):
        super().__init__()
        self.pt = pt
        self.style = style
        self.rubricID = rid
        self.kind = kind
        # centre under click
        self.di = DeltaItem(pt, delta, style=style, fontsize=fontsize)
        self.blurb = TextItem(
            pt,
            text,
            fontsize=fontsize,
            color=style["annot_color"],
            _texmaker=_scene,
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
        self.tweakPositions(delta, text)
        # hide delta if trivial
        if delta == ".":  # hide the delta
            self.di.setVisible(False)
        else:
            self.di.setVisible(True)
            self.addToGroup(self.di)
        # hide blurb if text is trivial
        if text == ".":  # hide the text
            self.blurb.setVisible(False)
        else:
            self.blurb.setVisible(True)
            self.addToGroup(self.blurb)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)

    def restyle(self, style):
        self.style = style
        self.thick = self.style["pen_width"] / 2
        # force a relatexing of the textitem in case it is a latex png
        self.blurb.restyle(style)
        self.di.restyle(style)

    def tweakPositions(self, delta, text):
        pt = self.pt
        self.blurb.setPos(pt)
        self.di.setPos(pt)
        # TODO: may want some special treatment in "." case
        # cr = self.di.boundingRect()
        # self.blurb.moveBy(cr.width() + 5, 0)

        # if no delta, then move things accordingly
        if delta == ".":
            cr = self.blurb.boundingRect()
            self.blurb.moveBy(0, -cr.height() / 2)
        elif text == ".":
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
        else:  # render both
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
            self.blurb.moveBy(cr.width() + 5, -cr.height() / 2)

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
            self.rubricID,
            self.kind,
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

    def sign_of_delta(self):
        if self.di.delta == ".":
            return 0
        elif int(self.di.delta) == 0:
            return 0
        elif int(self.di.delta) > 0:
            return 1
        else:
            return -1

    def is_delta_positive(self):
        if self.di.delta == ".":
            return False
        if int(self.di.delta) <= 0:
            return False
        return True

    def get_delta_value(self):
        if self.di.delta == ".":
            return 0
        else:
            return int(self.di.delta)


class GhostComment(QGraphicsItemGroup):
    def __init__(self, dlt, txt, fontsize):
        super().__init__()
        self.di = GhostDelta(dlt, fontsize)
        self.rubricID = "987654"  # a dummy value
        self.kind = "relative"  # another dummy value
        self.blurb = GhostText(txt, fontsize)
        self.changeComment(dlt, txt)
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def tweakPositions(self, dlt, txt):
        """Adjust the positions of the delta and text depending on their size and ontent."""
        pt = self.pos()
        self.blurb.setPos(pt)
        self.di.setPos(pt)

        # if no delta, then move things accordingly
        if dlt == ".":
            cr = self.blurb.boundingRect()
            self.blurb.moveBy(0, -cr.height() / 2)
        elif txt == ".":
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
        else:  # render both
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
            self.blurb.moveBy(cr.width() + 5, -cr.height() / 2)

    def changeComment(self, dlt, txt, legal=True):
        # need to force a bounding-rect update by removing an item and adding it back
        self.removeFromGroup(self.di)
        self.removeFromGroup(self.blurb)
        # change things
        self.di.changeDelta(dlt, legal)
        self.blurb.changeText(txt, legal)
        # move to correct positions
        self.tweakPositions(dlt, txt)
        if dlt == ".":  # hide the delta
            self.di.setVisible(False)
        else:
            self.di.setVisible(True)
            self.addToGroup(self.di)
        # hide blurb if text trivial
        if txt == ".":  # hide the text
            self.blurb.setVisible(False)
        else:
            self.blurb.setVisible(True)
            self.addToGroup(self.blurb)

    def paint(self, painter, option, widget):
        # paint a bounding rectangle for undo/redo highlighting
        # TODO: pen width hardcoded
        painter.setPen(QPen(Qt.blue, 0.5, style=Qt.DotLine))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
