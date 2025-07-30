# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# from enum import StrEnum

from enum import Enum


# class ClusteringType(StrEnum):
#     """Defines what type of clustering task to tackle on.

#     Attributes:
#         MCQ: Multiple choice question (A-F, a-f).
#         HME: Simple handwritten math expression.
#     """

#     MCQ = "mcq"
#     HME = "hme"


# temporary to test CI Pipeline
class ClusteringType(Enum):
    """Defines what clustering models used in clustering pipeline.

    Attributes:
        MCQ: Multiple choice question (A-F, a-f).
        HME: Simple handwritten math expression.
    """

    MCQ = 1
    HME = 2
