import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("BuildPaperPDF", "0001_initial"),
        ("Papers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="buildpaperpdfchore",
            name="paper",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="Papers.paper"
            ),
        ),
    ]
