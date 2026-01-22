from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PaperSourcePDF",
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
                ("source_pdf", models.FileField(upload_to="sourceVersions/")),
                ("pdf_hash", models.CharField(max_length=64)),
                ("original_filename", models.TextField()),
                ("page_count", models.PositiveIntegerField(blank=True, null=True)),
                ("paper_size_name", models.TextField(blank=True, null=True)),
                ("paper_size_width", models.FloatField(blank=True, null=True)),
                ("paper_size_height", models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="StagingStudent",
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
                ("student_id", models.TextField(null=True, unique=True)),
                ("student_name", models.TextField()),
                ("paper_number", models.PositiveIntegerField(null=True)),
            ],
        ),
    ]
