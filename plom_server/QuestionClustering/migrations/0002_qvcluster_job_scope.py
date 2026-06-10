# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

import django.db.models.deletion
from django.db import migrations, models


def backfill_cluster_jobs(apps, schema_editor):
    QVCluster = apps.get_model("QuestionClustering", "QVCluster")
    QuestionClusteringChore = apps.get_model(
        "QuestionClustering", "QuestionClusteringChore"
    )

    for cluster in QVCluster.objects.filter(job__isnull=True):
        job = (
            QuestionClusteringChore.objects.filter(
                question_idx=cluster.question_idx,
                version=cluster.version,
                page_num=cluster.page_num,
                top=cluster.top,
                left=cluster.left,
                bottom=cluster.bottom,
                right=cluster.right,
                obsolete=False,
            )
            .order_by("pk")
            .first()
        )
        if job is None:
            job = (
                QuestionClusteringChore.objects.filter(
                    question_idx=cluster.question_idx,
                    version=cluster.version,
                    page_num=cluster.page_num,
                    obsolete=False,
                )
                .order_by("pk")
                .first()
            )
        if job is not None:
            cluster.job = job
            cluster.save(update_fields=["job"])


class Migration(migrations.Migration):

    dependencies = [
        ("QuestionClustering", "0001_initial"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="qvcluster",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="qvcluster",
            name="job",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="clusters",
                to="QuestionClustering.questionclusteringchore",
            ),
        ),
        migrations.RunPython(backfill_cluster_jobs, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="qvcluster",
            unique_together={("job", "clusterId", "type")},
        ),
    ]
