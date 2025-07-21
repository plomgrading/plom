# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady


from django.db import models
from plom_server.Base.models import HueyTaskTracker
from plom_server.Papers.models import Paper


class ClusteringModelType(models.TextChoices):
    """Defines what clustering models exist in the system"""

    MCQ = "mcq", "Multiple choice (A-F, a-f)"
    HME = "hme", "Generic handwritten math expression"


class QuestionClusteringChore(HueyTaskTracker):
    """A tracker for the huey chore of clustering students' answer for a (question, version).

    question_idx: the question_index of the question being clustered
    version: the version of the question being clustered
    top: top left corner's y coordinate of the extracted rectangle used for clustering
    left: top left corner's x coordinate of the extracted rectangle used for clustering
    bottom: bottom right corner's y coordinate of the extracted rectangle used for clustering
    right: bottom right corner's x coordinate of the extracted rectangle used for clustering

    """

    question_idx = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)
    page_num = models.PositiveIntegerField(null=False)
    top = models.FloatField(null=False)
    left = models.FloatField(null=False)
    bottom = models.FloatField(null=False)
    right = models.FloatField(null=False)
    clustering_model = models.CharField(
        max_length=10, choices=ClusteringModelType.choices, null=False
    )

    def __str__(self):
        """Stringify task using its related question, version number."""
        return f"Cluster question: {self.question_idx}, version: {self.version}"


class QVCluster(models.Model):
    """A cluster in a (question, version) pair.

    question_idx: the question_index of the question being clustered
    version: the version of the question being clustered
    clusterId: the identifier used to differentiate clusters in a (question, version) pair

    top: top left corner's y coordinate of the extracted rectangle used for clustering
    left: top left corner's x coordinate of the extracted rectangle used for clustering
    bottom: bottom right corner's y coordinate of the extracted rectangle used for clustering
    right: bottom right corner's x coordinate of the extracted rectangle used for clustering
    """

    question_idx = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)
    page_num = models.PositiveIntegerField(null=False)
    clusterId = models.IntegerField(null=False)

    top = models.FloatField(null=False)
    left = models.FloatField(null=False)
    bottom = models.FloatField(null=False)
    right = models.FloatField(null=False)
    paper = models.ManyToManyField(Paper, through="QVClusterLink")

    class Meta:
        unique_together = ("question_idx", "version", "clusterId")


class QVClusterLink(models.Model):
    """Link a paper to a (q, v) cluster."""

    paper = models.ForeignKey(Paper, on_delete=models.CASCADE)
    qv_cluster = models.ForeignKey(QVCluster, on_delete=models.CASCADE)
