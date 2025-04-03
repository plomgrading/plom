import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("Base", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="IDPrediction",
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
                ("student_id", models.CharField(max_length=255, null=True)),
                ("predictor", models.CharField(max_length=255)),
                ("certainty", models.FloatField(default=0.0)),
            ],
        ),
        migrations.CreateModel(
            name="IDReadingHueyTaskTracker",
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
            ],
            bases=("Base.hueytasktracker",),
        ),
        migrations.CreateModel(
            name="IDRectangle",
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
                ("version", models.IntegerField(default=None, unique=True)),
                ("top", models.FloatField()),
                ("left", models.FloatField()),
                ("bottom", models.FloatField()),
                ("right", models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name="PaperIDAction",
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
                ("time", models.DateTimeField(default=django.utils.timezone.now)),
                ("is_valid", models.BooleanField(default=True)),
                ("student_name", models.TextField(default="", null=True)),
                ("student_id", models.TextField(default="", null=True)),
            ],
        ),
        migrations.CreateModel(
            name="PaperIDTask",
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
                ("iding_priority", models.FloatField(default=0.0, null=True)),
                ("time", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "status",
                    models.IntegerField(
                        choices=[
                            (1, "To Do"),
                            (2, "Out"),
                            (3, "Complete"),
                            (4, "Out Of Date"),
                        ],
                        default=1,
                    ),
                ),
                ("last_update", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
