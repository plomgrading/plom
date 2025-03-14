import django.core.validators
import django.db.models.deletion
import plom_server.Rubrics.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("Mark", "0001_initial"),
        ("QuestionTags", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Rubric",
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
                (
                    "rid",
                    models.IntegerField(
                        default=plom_server.Rubrics.models.generate_rid
                    ),
                ),
                (
                    "kind",
                    models.TextField(
                        choices=[
                            ("absolute", "Absolute"),
                            ("neutral", "Neutral"),
                            ("relative", "Relative"),
                        ]
                    ),
                ),
                ("display_delta", models.TextField(blank=True, default="")),
                ("value", models.FloatField(blank=True, default=0)),
                (
                    "out_of",
                    models.FloatField(
                        blank=True,
                        default=0,
                        validators=[django.core.validators.MinValueValidator(0.0)],
                    ),
                ),
                ("text", models.TextField()),
                ("question_index", models.IntegerField()),
                ("tags", models.TextField(blank=True, default="", null=True)),
                ("meta", models.TextField(blank=True, default="", null=True)),
                ("versions", models.JSONField(blank=True, default=list, null=True)),
                ("parameters", models.JSONField(blank=True, default=list, null=True)),
                ("system_rubric", models.BooleanField(blank=True, default=False)),
                ("published", models.BooleanField(blank=True, default=True)),
                ("last_modified", models.DateTimeField(auto_now=True)),
                ("revision", models.IntegerField(blank=True, default=0)),
                ("latest", models.BooleanField(blank=True, default=True)),
                (
                    "annotations",
                    models.ManyToManyField(blank=True, to="Mark.annotation"),
                ),
                (
                    "modified_by_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "pedagogy_tags",
                    models.ManyToManyField(blank=True, to="QuestionTags.pedagogytag"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RubricPane",
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
                ("question", models.PositiveIntegerField(default=0)),
                ("data", models.JSONField(default=dict)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
