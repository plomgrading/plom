# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from plom_ml.clustering.model.model_type import ClusteringType
from plom_ml.clustering.model.clustering_strategy import (
    ClusteringStrategy,
    MCQClusteringStrategy,
    HMEClusteringStrategy,
)

from functools import lru_cache


@lru_cache()
def get_ClusteringStrategy(model_type: ClusteringType) -> ClusteringStrategy:
    """Load and cache one ClusteringStrategy instance per type, per process.

    Note: we use @lru_cache to reduce memory blow-up due to multiple model instantiations
    for same task.
    """
    if model_type == ClusteringType.MCQ:
        return MCQClusteringStrategy()
    elif model_type == ClusteringType.HME:
        return HMEClusteringStrategy()
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
