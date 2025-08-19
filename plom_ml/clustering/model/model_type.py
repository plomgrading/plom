# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

# from enum import StrEnum

from enum import Enum


class ClusteringType(str, Enum):
    """Defines what type of clustering task to tackle on.

    Attributes:
        MCQ: Multiple choice question (A-F, a-f).
        HME: Simple handwritten math expression.
    """

    MCQ = "mcq"
    HME = "hme"
