import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("Base", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BuildPaperPDFChore",
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
                ("pdf_file", models.FileField(null=True, upload_to="papersToPrint/")),
                ("display_filename", models.TextField(null=True)),
                ("student_name", models.TextField(default=None, null=True)),
                ("student_id", models.TextField(default=None, null=True)),
            ],
            bases=("Base.hueytasktracker",),
        ),
    ]
