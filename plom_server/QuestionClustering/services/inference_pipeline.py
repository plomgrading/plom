import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from pathlib import Path
from plom_server.QuestionClustering.models import ClusteringModelType
from plom_server.QuestionClustering.services.clustering_models import (
    ClusteringModel,
    MCQClusteringModel,
)
from functools import lru_cache
import pandas as pd
from typing import Sequence, Mapping
from .preprocessor import Preprocessor


@lru_cache()
def get_model(model_type: ClusteringModelType) -> ClusteringModel:
    """Lazily load and cache one model instance per type, per process"""
    if model_type == ClusteringModelType.MCQ:
        return MCQClusteringModel()
    # elif model_type == ClusteringModel.HME:
    else:
        raise ValueError(f"Unsupported model type: {model_type}")


class ClusteringPipeline:
    """A wrapper to use clustering model for inference.

    The wrapper lazy loads and caches the model, so every inference of the same type
    uses the same loaded model.
    """

    def __init__(self, model_type: ClusteringModelType, preprocessor: Preprocessor):
        self.preprocessor = preprocessor
        self.model = get_model(model_type)

    def cluster(
        self, paper_to_images: Mapping[int, Sequence[np.ndarray]]
    ) -> dict[int, int]:
        """Cluster the given papers with the given preprocessor and clustering model.

        Args:
            paper_to_image: a dictionary mapping paper number to one or more images
                representing that paper.
                Note: We may need multiple input images, eg: we need the blank and the scanned
                representation of the page to extract the handwritten strokes.


        Returns:
            A dictionary mapping the paper number to their cluster id
        """

        # Preprocess the images
        preprocessed_paper_to_images = {
            pn: self.preprocessor.process(*images)
            for pn, images in paper_to_images.items()
        }
        return self.model.cluster_papers(preprocessed_paper_to_images)
