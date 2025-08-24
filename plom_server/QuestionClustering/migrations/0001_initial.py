import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("Base", "0001_initial"),
        ("Papers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionClusteringChore",
            fields=[
                (
                    "hueytasktracker_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="Base.hueytasktracker",
                    ),
                ),
                ("question_idx", models.PositiveIntegerField()),
                ("version", models.PositiveIntegerField()),
                ("page_num", models.PositiveIntegerField()),
                ("top", models.FloatField()),
                ("left", models.FloatField()),
                ("bottom", models.FloatField()),
                ("right", models.FloatField()),
                (
                    "clustering_model",
                    models.CharField(
                        choices=[
                            ("mcq", "Multiple choice (A-F, a-f)"),
                            ("hme", "Generic handwritten math expression"),
                        ],
                        max_length=10,
                    ),
                ),
            ],
            bases=("Base.hueytasktracker",),
        ),
        migrations.CreateModel(
            name="QVCluster",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("question_idx", models.PositiveIntegerField()),
                ("version", models.PositiveIntegerField()),
                ("page_num", models.PositiveIntegerField()),
                ("clusterId", models.IntegerField(blank=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("original", "Original clustering created"),
                            ("user_facing", "Clustering group that user sees"),
                        ],
                        max_length=20,
                    ),
                ),
                ("top", models.FloatField()),
                ("left", models.FloatField()),
                ("bottom", models.FloatField()),
                ("right", models.FloatField()),
                (
                    "user_cluster",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"type": "user_facing"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="original_cluster",
                        to="QuestionClustering.qvcluster",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="QVClusterLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "paper",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="Papers.paper"
                    ),
                ),
                (
                    "qv_cluster",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="QuestionClustering.qvcluster",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="qvcluster",
            name="paper",
            field=models.ManyToManyField(
                through="QuestionClustering.QVClusterLink", to="Papers.paper"
            ),
        ),
        migrations.AddConstraint(
            model_name="qvcluster",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("type", "user_facing"), ("user_cluster__isnull", True)),
                    models.Q(("type", "user_facing"), _negated=True),
                    _connector="OR",
                ),
                name="cluster_type_user_cluster_consistency",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="qvcluster",
            unique_together={("question_idx", "version", "clusterId", "type")},
        ),
    ]
