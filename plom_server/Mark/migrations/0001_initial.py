import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("Papers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AnnotationImage",
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
                ("image", models.FileField(upload_to="annotation_images/")),
                ("hash", models.TextField(default="")),
            ],
        ),
        migrations.CreateModel(
            name="Annotation",
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
                ("edition", models.IntegerField(null=True)),
                ("score", models.FloatField(null=True)),
                ("annotation_data", models.JSONField(null=True)),
                ("marking_time", models.FloatField(null=True)),
                ("marking_delta_time", models.FloatField(null=True)),
                ("time_of_last_update", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "image",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="Mark.annotationimage",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MarkingTask",
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
                ("code", models.TextField(default="")),
                ("question_index", models.PositiveIntegerField(default=0)),
                ("question_version", models.PositiveIntegerField(default=0)),
                ("marking_priority", models.FloatField(default=0.0)),
                (
                    "assigned_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "latest_annotation",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="Mark.annotation",
                    ),
                ),
                (
                    "paper",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="Papers.paper"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="annotation",
            name="task",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="Mark.markingtask",
            ),
        ),
        migrations.CreateModel(
            name="MarkingTaskTag",
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
                ("time", models.DateField(default=django.utils.timezone.now)),
                ("text", models.TextField()),
                ("task", models.ManyToManyField(to="Mark.markingtask")),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
