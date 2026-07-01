# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Deep Shah

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("QuestionClustering", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="qvcluster",
            name="cluster_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
