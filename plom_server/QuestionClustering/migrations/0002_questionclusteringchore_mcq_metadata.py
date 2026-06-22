# Generated manually for MCQ option-box metadata storage.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("QuestionClustering", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="questionclusteringchore",
            name="mcq_metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
