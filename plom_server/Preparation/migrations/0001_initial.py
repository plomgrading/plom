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
                ("hash", models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name="StagingPQVMapping",
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
                ("paper_number", models.PositiveIntegerField()),
                ("question", models.PositiveIntegerField()),
                ("version", models.PositiveIntegerField()),
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
