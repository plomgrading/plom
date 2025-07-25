# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady


class ClusteringCleanupError(Exception):
    """Base exception for clustering-cleanup related operations."""


class NoSelectedClusterError(ClusteringCleanupError):
    """Exception when there is no selected cluster in selecting-based operations."""
