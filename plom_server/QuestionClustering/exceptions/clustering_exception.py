# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady


class ClusteringCleanupError(Exception):
    """Base exception for clustering-cleanup related operations."""

    pass


class EmptySelectedError(ClusteringCleanupError):
    """Exception when there is no selection in selecting-based operations."""

    pass
