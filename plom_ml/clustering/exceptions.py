# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bran Tanady
"""Exceptions for clustering module."""
from plom_ml.exceptions import PlomMLException


class ClusteringException(PlomMLException):
    """A base exception for clustering related module."""

    pass


class PreprocessingException(ClusteringException):
    """Preprocessing steps related exception."""

    pass


class MissingRequiredInputKeys(PreprocessingException):
    """Input images are missing required keys required by the preprocessor."""

    pass


class EmbeddingExceptions(ClusteringException):
    """Embedding steps related exception."""

    pass
