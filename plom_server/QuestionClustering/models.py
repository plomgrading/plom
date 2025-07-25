# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady


from django.db import models
from plom_server.Base.models import HueyTaskTracker
from plom_server.Papers.models import Paper
from django.db.models import Q
from django.db.models import Max
from django.db import transaction

from plom_ml.clustering.model_type import ClusteringModelType as MLClusteringModelType


class ClusteringModelType(models.TextChoices):
    """Define clustering types supported by plom."""

    MCQ = MLClusteringModelType.MCQ.value, "Multiple choice (A-F, a-f)"
    HME = MLClusteringModelType.HME.value, "Generic handwritten math expression"


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
        max_length=10,
        choices=ClusteringModelType.choices,
        null=False,
    )

    def __str__(self):
        """Stringify task using its related question, version number."""
        return f"Cluster question: {self.question_idx}, version: {self.version}"


class ClusteringGroupType(models.TextChoices):
    """Defines what clustering models exist in the system."""

    original = "original", "Original clustering created"
    user_facing = "user_facing", "Clustering group that user sees"


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
    clusterId = models.IntegerField(blank=True, null=False)
    type = models.CharField(
        choices=ClusteringGroupType.choices, null=False, max_length=20
    )
    user_cluster = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="original_cluster",
        limit_choices_to={"type": ClusteringGroupType.user_facing},
    )

    top = models.FloatField(null=False)
    left = models.FloatField(null=False)
    bottom = models.FloatField(null=False)
    right = models.FloatField(null=False)
    paper = models.ManyToManyField(Paper, through="QVClusterLink")

    class Meta:
        unique_together = ("question_idx", "version", "clusterId", "type")
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(type=ClusteringGroupType.user_facing, user_cluster__isnull=True)
                    | ~Q(type=ClusteringGroupType.user_facing)
                ),
                name="cluster_type_user_cluster_consistency",
            )
        ]

    def save(self, *args, **kwargs):
        # Only assign if no value given
        if self.clusterId in (None, ""):
            # atomic to avoid two processes picking the same next ID
            with transaction.atomic():
                last = (
                    QVCluster.objects.filter(
                        question_idx=self.question_idx, version=self.version
                    ).aggregate(Max("clusterId"))["clusterId__max"]
                ) or 0
                self.clusterId = last + 1

        super().save(*args, **kwargs)


class QVClusterLink(models.Model):
    """Link a paper to a (q, v) cluster."""

    paper = models.ForeignKey(Paper, on_delete=models.CASCADE)
    qv_cluster = models.ForeignKey(QVCluster, on_delete=models.CASCADE)
