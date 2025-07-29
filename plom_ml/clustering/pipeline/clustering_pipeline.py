# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady

# plom_ml
from plom_ml.clustering.model.clustering_model import (
    ClusteringModel,
)
from plom_ml.clustering.preprocessing.preprocessor import Preprocessor

# misc
import numpy as np
from typing import Mapping


class ClusteringPipeline:
    """A wrapper to use clustering model for inference that outputs paper_num to clusterId map.

    Args:
        model_type: The type of clustering model to use.
        preprocessor: The preprocessing pipeline applied before inference.
    """

    def __init__(self, model: ClusteringModel, preprocessor: Preprocessor):
        self.preprocessor = preprocessor
        self.model = model

    def cluster(
        self, paper_to_images: Mapping[int, dict[str, np.ndarray]]
    ) -> dict[int, int]:
        """Cluster the given papers with the given preprocessor and clustering model.

        Args:
            paper_to_images: a dictionary mapping paper number to another dict each represents an image.
                The key of the image depends on the chosen preprocessor.

                Note: images are made as a sequence because We may need more than one input images,
                    eg: we need the blank and the scanned representation of the page to
                    extract the handwritten strokes.


        Returns:
            A dictionary mapping the paper number to their cluster id.
        """
        # Preprocess the images
        processed_paper_to_images = {
            pn: self.preprocessor.process(images)
            for pn, images in paper_to_images.items()
        }

        # Feed the processed inputs to the model
        return self.model.cluster_papers(processed_paper_to_images)
