# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2021 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2024 Bryan Tanady

from copy import deepcopy
from typing import Union

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QFont, QPen
from PyQt6.QtWidgets import QGraphicsItemGroup, QGraphicsItem

from plom.client.tools import OutOfBoundsPen, OutOfBoundsFill
from plom.client.tools import CommandTool, UndoStackMoveMixin
from plom.client.tools.delta import DeltaItem, GhostDelta
from plom.client.tools.text import GhostText, TextItem


class CommandRubric(CommandTool):
    """A group of marks and text.

    Command to do a delta and a textitem together (a "rubric" or
    "saved comment").
    """

    def __init__(self, scene, pt, rubric):
        """Constructor for this class.

        Args:
            scene (PageScene): Plom's annotation scene.
            pt (QPointF): where to place the rubric.
            rubric (dict): must have at least these keys:
                "id", "kind", "value", "out_of", "display_delta", "text".
                Any other keys are probably ignored and will almost
                certainly not survive being serialized.
                We copy the data, so changes to the original will not
                automatically update this object,
        """
        super().__init__(scene)
        self.gdt = RubricItem(pt, rubric, _scene=scene, style=scene.style)
        self.setText("Rubric")

    @classmethod
    def from_pickle(cls, X, *, scene):
        """Construct a CommandRubric from a serialized RubricItem.

        TODO: could this comandFoo.__init__() take a FooItem?
        """
        assert X[0] == "Rubric"
        X = X[1:]
        if len(X) != 9:
            raise ValueError("wrong length of pickle data")
        # knows to latex it if needed.
        return cls(
            scene,
            QPointF(X[0], X[1]),
            {
                "id": X[2],
                "kind": X[3],
                "value": X[4],
                "out_of": X[5],
                "display_delta": X[6],
                "text": X[7],
                "tags": X[8],
            },
        )

    def get_undo_redo_animation_shape(self):
        return self.gdt.shape()

    def redo(self):
        self.scene.addItem(self.gdt)
        self.redo_animation()

    def undo(self):
        self.scene.removeItem(self.gdt)
        self.undo_animation()


class RubricItem(UndoStackMoveMixin, QGraphicsItemGroup):
    """A group of Delta and Text presenting a rubric.

    TODO: passing in scene is a workaround so the TextItem can talk to
    someone about building LaTeX... can we refactor that somehow?
    """

    def __init__(self, pt, rubric, *, _scene, style):
        """Constructor for this class.

        Args:
            pt (QPointF): where to place the rubric.
            rubric (dict): must have at least these keys:
                "id", "kind", "value", "out_of", "display_delta", "text".
                Any other keys are probably ignored and will almost
                certainly not survive being serialized.
                We copy the data, so changes to the original will not
                automatically update this object,

        Keyword Args:
            _scene (PageScene): Plom's annotation scene.
            style (dict): various things effecting color, linewidths etc.

        Returns:
            None
        """
        super().__init__()
        self.pt = pt
        self.style = style
        self._rubric = deepcopy(rubric)
        # TODO: replace each with @property?
        self.rubricID = rubric["id"]
        self.kind = rubric["kind"]
        # centre under click
        self.di = DeltaItem(pt, rubric["value"], rubric["display_delta"], style=style)
        self.blurb = TextItem(pt, rubric["text"], style=style, _texmaker=_scene)
        # TODO: probably we "restyle" the child objects twice as each init did this too
        self.restyle(style)
        # Set the underlying delta and text to not pickle - since the GDTI will handle that
        self.saveable = True
        self.di.saveable = False
        self.blurb.saveable = False

        # TODO: the blurb will do this anyway, but may defer this to "later",
        # meanwhile we have the wrong size for tweakPositions (Issue #1391).
        # TODO: can be removed once the border adjusts automatically to resize.
        self.blurb.textToPng()

        # move blurb so that its top-left corner is next to top-right corner of delta.
        self._tweakPositions(rubric["display_delta"], rubric["text"])
        # hide delta if trivial
        if rubric["display_delta"] == ".":
            self.di.setVisible(False)
        else:
            self.di.setVisible(True)
            self.addToGroup(self.di)
        # hide blurb if text is trivial
        if rubric["text"] == ".":
            self.blurb.setVisible(False)
        else:
            self.blurb.setVisible(True)
            self.addToGroup(self.blurb)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

    def as_rubric(self):
        """Return as a rubric dict."""
        return {
            "id": self.rubricID,
            "kind": self.kind,
            "display_delta": self.di.display_delta,
            "value": self.di.value,
            "out_of": self._rubric["out_of"],
            "text": self.blurb.toPlainText(),
            "tags": self._rubric["tags"],
        }

    def restyle(self, style):
        self.style = style
        self.thick = self.style["pen_width"] / 2
        # force a relatexing of the textitem in case it is a latex png
        self.blurb.restyle(style)
        self.di.restyle(style)

    def _tweakPositions(self, display_delta, text):
        pt = self.pt
        self.blurb.setPos(pt)
        self.di.setPos(pt)
        # TODO: may want some special treatment in "." case
        # cr = self.di.boundingRect()
        # self.blurb.moveBy(cr.width() + 5, 0)

        # if no display_delta, then move things accordingly
        if display_delta == ".":
            cr = self.blurb.boundingRect()
            self.blurb.moveBy(0, -cr.height() / 2)
        elif text == ".":
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
        else:  # render both
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
            self.blurb.moveBy(cr.width() + 5, -cr.height() / 2)

    def pickle(self):
        return [
            "Rubric",
            self.pt.x() + self.x(),
            self.pt.y() + self.y(),
            self.rubricID,
            self.kind,
            self.di.value,
            self._rubric["out_of"],
            self.di.display_delta,
            self.blurb.toPlainText(),
            self._rubric["tags"],
        ]

    def paint(self, painter, option, widget):
        if not self.scene().itemWithinBounds(self):
            painter.setPen(OutOfBoundsPen)
            painter.setBrush(OutOfBoundsFill)
            painter.drawLine(option.rect.topLeft(), option.rect.bottomRight())
            painter.drawLine(option.rect.topRight(), option.rect.bottomLeft())
            painter.drawRoundedRect(option.rect, 10, 10)
        else:
            # paint a bounding rectangle for undo/redo highlighting
            painter.setPen(
                QPen(self.style["annot_color"], self.thick, style=Qt.PenStyle.DotLine)
            )
            painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)

    def sign_of_delta(self):
        if int(self.di.value) == 0:
            return 0
        elif int(self.di.value) > 0:
            return 1
        else:
            return -1

    def is_delta_positive(self):
        return int(self.di.value) > 0

    def get_delta_value(self):
        return int(self.di.value)


class GhostComment(QGraphicsItemGroup):
    def __init__(self, annot_scale: float, display_delta: str, txt: str, fontsize: int):
        super().__init__()
        self.legal = False
        self.annot_scale = annot_scale
        self.di = GhostDelta(display_delta, fontsize, legal=self.legal)
        self.blurb = GhostText(txt, annot_scale, fontsize, legal=self.legal)
        self.changeComment(display_delta, txt)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

    def _tweakPositions(self, display_delta, txt):
        """Adjust the positions of the delta and text depending on their size and content.

        Note: does not fix up the size of the boxes, see changeComment which does.
        """
        pt = self.pos()
        # Offset is physical unit which will cause the gap gets bigger when zoomed in.
        offset = 0
        shifted_pt = QPointF(pt.x() + offset, pt.y())
        self.blurb.setPos(shifted_pt)
        self.di.setPos(shifted_pt)

        # if no delta, then move things accordingly
        if display_delta == ".":
            cr = self.blurb.boundingRect()
            self.blurb.moveBy(0, -cr.height() / 2)
        elif txt == ".":
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
        else:  # render both
            cr = self.di.boundingRect()
            self.di.moveBy(0, -cr.height() / 2)
            self.blurb.moveBy(cr.width() + 5, -cr.height() / 2)

    def changeComment(self, display_delta, txt, legal=True):
        # need to force a bounding-rect update by removing an item and adding it back
        self.removeFromGroup(self.di)
        self.removeFromGroup(self.blurb)
        # change things
        self.legal = legal
        self.di.changeDelta(display_delta, legal)
        self.blurb.update_annot_scale(self.annot_scale)
        self.blurb.changeText(txt, legal)
        # move to correct positions
        self._tweakPositions(display_delta, txt)
        if display_delta == ".":  # hide the delta
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

    def change_rubric_size(
        self, fontsize: Union[int, None], annot_scale: float
    ) -> None:
        """Change comment size.

        Args:
            fontsize: the fontsize that will be applied in the comment.
            annot_scale: the scene's global scale.
        """
        if not fontsize:
            fontsize = 10

        font = QFont("Helvetica")
        font.setPixelSize(round(fontsize))
        self.blurb.setFont(font)
        font = QFont("Helvetica")
        font.setPixelSize(round(1.25 * fontsize))
        self.di.setFont(font)
        self.annot_scale = annot_scale
        self.changeComment(
            self.di.display_delta, self.blurb.toPlainText(), legal=self.legal
        )

    def paint(self, painter, option, widget):
        # paint a bounding rectangle for undo/redo highlighting
        # TODO: pen width hardcoded
        painter.setPen(QPen(QColor("blue"), 0.5, style=Qt.PenStyle.DotLine))
        painter.drawRoundedRect(option.rect, 10, 10)
        # paint the normal item with the default 'paint' method
        super().paint(painter, option, widget)
