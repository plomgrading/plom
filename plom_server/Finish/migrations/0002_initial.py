import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("Finish", "0001_initial"),
        ("Papers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="buildsolutionpdfchore",
            name="paper",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="Papers.paper"
            ),
        ),
        migrations.AddField(
            model_name="reassemblepaperchore",
            name="paper",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="Papers.paper"
            ),
        ),
    ]
