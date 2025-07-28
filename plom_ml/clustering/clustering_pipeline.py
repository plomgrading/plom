# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

import numpy as np
from plom_server.QuestionClustering.models import ClusteringModelType
from .clustering_models import (
    ClusteringModel,
    MCQClusteringModel,
    HMEClusteringModel,
)
from functools import lru_cache
from typing import Sequence, Mapping
from .preprocessor import Preprocessor


@lru_cache()
def get_model(model_type: ClusteringModelType) -> ClusteringModel:
    """Lazily load and cache one model instance per type, per process.

    Note: we use @lru_cache to reduce memory blow-up due to multiple model instantiations.
    """
    if model_type == ClusteringModelType.MCQ:
        return MCQClusteringModel()
    elif model_type == ClusteringModelType.HME:
        return HMEClusteringModel()
    else:
        raise ValueError(f"Unsupported model type: {model_type}")


class ClusteringPipeline:
    """A wrapper to use clustering model for inference that outputs paper_num to clusterId map.

    The wrapper caches the model so every inference of the same type and
    same process uses the same loaded model .

    Args:
        model_type: The type of clustering model to use.
        preprocessor: The preprocessing pipeline applied before inference.
    """

    def __init__(self, model_type: ClusteringModelType, preprocessor: Preprocessor):
        self.preprocessor = preprocessor
        self.model = get_model(model_type)

    def cluster(
        self, paper_to_images: Mapping[int, Sequence[np.ndarray]]
    ) -> dict[int, int]:
        """Cluster the given papers with the given preprocessor and clustering model.

        Args:
            paper_to_images: a dictionary mapping paper number to one or more images
                representing that paper.

                Note: images are made as a sequence because We may need more than one input images,
                    eg: we need the blank and the scanned representation of the page to
                    extract the handwritten strokes.


        Returns:
            A dictionary mapping the paper number to their cluster id.
        """
        # Preprocess the images
        processed_paper_to_images = {
            pn: self.preprocessor.process(*images)
            for pn, images in paper_to_images.items()
        }

        # Feed the processed inputs to the model
        return self.model.cluster_papers(processed_paper_to_images)
