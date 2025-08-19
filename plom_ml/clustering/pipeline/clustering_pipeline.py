# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

from typing import Mapping

import numpy as np

from plom_ml.clustering.model.clustering_strategy import (
    ClusteringStrategy,
)
from plom_ml.clustering.preprocessing.preprocessor import Preprocessor


class ClusteringPipeline:
    """A pipeline for clustering inference composed of clustering model and preprocessor.

    Args:
        model: The clustering model used in the pipeline.
        preprocessor: The preprocessing pipeline applied before inference.
    """

    def __init__(
        self, ClusteringStrategy: ClusteringStrategy, preprocessor: Preprocessor
    ):
        self.preprocessor = preprocessor
        self.ClusteringStrategy = ClusteringStrategy

    def cluster(
        self, paper_to_images: Mapping[int, Mapping[str, np.ndarray]]
    ) -> dict[int, int]:
        """Cluster the given papers with the given preprocessor and ClusteringStrategy.

        Args:
            paper_to_images: a dictionary mapping paper number to another dict each represents an image.
                The key of the image depends on the chosen preprocessor.

                Note: paper can be mapped to multiple images because we may need more
                    than one input images,
                    eg: we need the blank and the scanned representation of the page to
                    extract the handwritten strokes.


        Returns:
            A dictionary mapping paper number to their cluster id.
        """
        # Preprocess the images
        processed_paper_to_images = {
            pn: self.preprocessor.process(images)
            for pn, images in paper_to_images.items()
        }

        # Feed the processed inputs to the model
        return self.ClusteringStrategy.cluster_papers(processed_paper_to_images)
