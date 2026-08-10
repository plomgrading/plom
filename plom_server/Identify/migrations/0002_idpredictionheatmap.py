import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Identify", "0001_initial"),
        ("Papers", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="IDPredictionHeatmap",
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
                ("source_image_hash", models.CharField(max_length=64)),
                ("probabilities", models.JSONField()),
                ("time", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_update", models.DateTimeField(auto_now=True)),
                (
                    "paper",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="Papers.paper",
                    ),
                ),
            ],
        ),
    ]
