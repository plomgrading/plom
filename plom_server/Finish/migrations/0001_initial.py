import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("Base", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BuildSolutionPDFChore",
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
                ("pdf_file", models.FileField(null=True, upload_to="solutions/")),
                ("display_filename", models.TextField(null=True)),
            ],
            bases=("Base.hueytasktracker",),
        ),
        migrations.CreateModel(
            name="ReassemblePaperChore",
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
                ("pdf_file", models.FileField(null=True, upload_to="reassembled/")),
                ("display_filename", models.TextField(null=True)),
                (
                    "report_pdf_file",
                    models.FileField(null=True, upload_to="student_report/"),
                ),
                ("report_display_filename", models.TextField(null=True)),
            ],
            bases=("Base.hueytasktracker",),
        ),
        migrations.CreateModel(
            name="SolutionImage",
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
                ("version", models.PositiveIntegerField()),
                ("solution_number", models.PositiveIntegerField()),
                (
                    "image",
                    models.ImageField(
                        height_field="height",
                        upload_to="sourceVersions",
                        width_field="width",
                    ),
                ),
                ("height", models.IntegerField(default=0)),
                ("width", models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="SolutionSourcePDF",
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
                ("version", models.PositiveIntegerField(unique=True)),
                ("source_pdf", models.FileField(upload_to="sourceVersions")),
                ("pdf_hash", models.CharField(max_length=64)),
            ],
        ),
    ]
