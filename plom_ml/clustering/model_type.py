# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
from enum import Enum


class ClusteringModelType(Enum):
    """Defines what clustering models used in clustering pipeline.

    Attributes:
        MCQ: Multiple choice question (A-F, a-f).
        HME: Simple handwritten math expression.
    """

    MCQ = "mcq"
    HME = "hme"
