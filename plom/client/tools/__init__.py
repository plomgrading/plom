# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2019 Andrew Rechnitzer
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2022, 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

import logging

log = logging.getLogger("tools")

from PyQt6.QtGui import QColor

# rough length of animations take in milliseconds: some might be shorter,
# some longer but they will be scaled by this value.
AnimationDuration: int = 200
AnimationPenColour = QColor(8, 232, 222, 128)
AnimationPenThickness = 10
AnimationFillColour = QColor(8, 232, 222, 16)

from plom.client.tools.move import CommandMoveItem, UndoStackMoveMixin
from plom.client.tools.tool import CommandTool, DeleteObject, DeleteItem
from plom.client.tools.delete import CommandDelete
from plom.client.tools.crop import CommandCrop
from plom.client.tools.rotate_page import CommandRotatePage
from plom.client.tools.shift_page import CommandShiftPage

from plom.client.tools.box import CommandBox
from plom.client.tools.rubric import (
    CommandRubric,
    RubricItem,
    GhostComment,
)
from plom.client.tools.cross import CommandCross, CrossItem
from plom.client.tools.delta import GhostDelta, DeltaItem
from plom.client.tools.ellipse import CommandEllipse
from plom.client.tools.highlight import CommandHighlight
from plom.client.tools.image import CommandImage, ImageItem
from plom.client.tools.line import CommandLine
from plom.client.tools.arrow import CommandArrow, CommandArrowDouble
from plom.client.tools.pen import CommandPen
from plom.client.tools.penArrow import CommandPenArrow
from plom.client.tools.questionMark import CommandQMark
from plom.client.tools.text import CommandText, TextItem, GhostText
from plom.client.tools.tick import CommandTick, TickItem
