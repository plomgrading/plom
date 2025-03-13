import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="HueyTaskTracker",
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
                ("huey_id", models.UUIDField(null=True)),
                (
                    "status",
                    models.IntegerField(
                        choices=[
                            (1, "To Do"),
                            (2, "Starting"),
                            (3, "Queued"),
                            (4, "Running"),
                            (5, "Complete"),
                            (6, "Error"),
                        ],
                        default=1,
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(blank=True, default=django.utils.timezone.now),
                ),
                ("message", models.TextField(default="")),
                ("last_update", models.DateTimeField(auto_now=True)),
                ("obsolete", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="SettingsModel",
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
                ("who_can_create_rubrics", models.TextField(default="permissive")),
                ("who_can_modify_rubrics", models.TextField(default="per-user")),
                ("feedback_rules", models.JSONField(default=dict)),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
