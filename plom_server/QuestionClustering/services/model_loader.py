# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from plom_ml.clustering.model.model_type import ClusteringModelType
from plom_ml.clustering.model.clustering_model import (
    ClusteringModel,
    MCQClusteringModel,
    HMEClusteringModel,
)

from functools import lru_cache


@lru_cache()
def get_model(model_type: ClusteringModelType) -> ClusteringModel:
    """Load and cache one model instance per type, per process.

    Note: we use @lru_cache to reduce memory blow-up due to multiple model instantiations.
    """
    if model_type == ClusteringModelType.MCQ:
        return MCQClusteringModel()
    elif model_type == ClusteringModelType.HME:
        return HMEClusteringModel()
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
