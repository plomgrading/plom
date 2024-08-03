# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2019 Andrew Rechnitzer
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2022, 2024 Colin B. Macdonald
# Copyright (C) 2024 Aden Chan

import logging

log = logging.getLogger("tools")

from PyQt6.QtGui import QBrush, QColor, QPen

OutOfBoundsPenColour = QColor(255, 165, 0)
OutOfBoundsFillColour = QColor(255, 165, 0, 128)
OutOfBoundsPen = QPen(OutOfBoundsPenColour, 8)
OutOfBoundsFill = QBrush(OutOfBoundsFillColour)

DefaultTickRadius = 20
DefaultPenWidth = 2
# I don't know what units this is, especially after Issue #1071.
# see also, ScenePixelHeight in plom __init__
AnnFontSizePts = 34.0

from plom.client.tools.move import CommandMoveItem, UndoStackMoveMixin
from plom.client.tools.tool import CommandTool
from plom.client.tools.delete import CommandDelete
from plom.client.tools.crop import CommandCrop
from plom.client.tools.rotate_page import CommandRotatePage
from plom.client.tools.shift_page import CommandShiftPage
from plom.client.tools.remove_page import CommandRemovePage

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
