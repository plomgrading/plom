# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady


class ClusteringJobError(Exception):
    """Base exception for clustering job."""

    pass


class DuplicateClusteringJobError(ClusteringJobError):
    """Raised when trying to create a duplicate clsutering job."""

    pass
