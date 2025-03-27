import django.db.models.deletion
import plom_server.Papers.models.image_bundle
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("Base", "0001_initial"),
        ("Preparation", "0001_initial"),
        ("Scan", "0001_initial"),
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FixedPage",
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
                ("page_number", models.PositiveIntegerField()),
                ("version", models.PositiveIntegerField()),
                (
                    "polymorphic_ctype",
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="polymorphic_%(app_label)s.%(class)s_set+",
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
        ),
        migrations.CreateModel(
            name="NumberOfPapersToProduceSetting",
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
                ("number_of_papers", models.PositiveIntegerField(default=0)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Paper",
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
                ("paper_number", models.PositiveIntegerField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="PopulateEvacuateDBChore",
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
                (
                    "action",
                    models.IntegerField(
                        choices=[(1, "Populate"), (2, "Evacuate")], default=1
                    ),
                ),
            ],
            bases=("Base.hueytasktracker",),
        ),
        migrations.CreateModel(
            name="SolnSpecification",
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
                ("numberOfPages", models.PositiveIntegerField()),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SolnSpecQuestion",
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
                ("pages", models.JSONField()),
                ("solution_number", models.PositiveIntegerField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Specification",
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
                ("name", models.TextField()),
                ("longName", models.TextField()),
                ("numberOfVersions", models.PositiveIntegerField()),
                ("numberOfPages", models.PositiveIntegerField()),
                ("numberOfQuestions", models.PositiveIntegerField()),
                ("totalMarks", models.PositiveIntegerField()),
                ("privateSeed", models.TextField()),
                ("publicCode", models.TextField()),
                ("idPage", models.PositiveIntegerField()),
                ("doNotMarkPages", models.JSONField()),
                ("allowSharedPages", models.BooleanField(default=False)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SpecQuestion",
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
                ("pages", models.JSONField()),
                ("mark", models.PositiveIntegerField()),
                (
                    "select",
                    models.CharField(
                        choices=[("fix", "fix"), ("shuffle", "shuffle")],
                        default="shuffle",
                        max_length=7,
                    ),
                ),
                ("label", models.TextField(null=True)),
                ("question_index", models.PositiveIntegerField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Bundle",
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
                ("name", models.TextField()),
                ("hash", models.CharField(max_length=64)),
                ("_is_system", models.BooleanField(default=False)),
                ("time_of_last_update", models.DateTimeField(auto_now=True)),
                (
                    "staging_bundle",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="Scan.stagingbundle",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="CreateImageHueyTask",
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
                (
                    "staging_image",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="Scan.stagingimage",
                    ),
                ),
            ],
            bases=("Base.hueytasktracker",),
        ),
        migrations.CreateModel(
            name="DNMPage",
            fields=[
                (
                    "fixedpage_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="Papers.fixedpage",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("Papers.fixedpage",),
        ),
        migrations.CreateModel(
            name="IDPage",
            fields=[
                (
                    "fixedpage_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="Papers.fixedpage",
                    ),
                ),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("Papers.fixedpage",),
        ),
        migrations.CreateModel(
            name="QuestionPage",
            fields=[
                (
                    "fixedpage_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="Papers.fixedpage",
                    ),
                ),
                ("question_index", models.PositiveIntegerField()),
            ],
            options={
                "abstract": False,
                "base_manager_name": "objects",
            },
            bases=("Papers.fixedpage",),
        ),
        migrations.CreateModel(
            name="Image",
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
                ("bundle_order", models.PositiveIntegerField(null=True)),
                ("original_name", models.TextField(null=True)),
                (
                    "image_file",
                    models.ImageField(
                        height_field="height",
                        upload_to=plom_server.Papers.models.image_bundle.Image._image_upload_path,
                        width_field="width",
                    ),
                ),
                ("hash", models.CharField(max_length=64, null=True)),
                ("rotation", models.IntegerField(default=0)),
                ("parsed_qr", models.JSONField(default=dict, null=True)),
                ("height", models.IntegerField(default=0)),
                ("width", models.IntegerField(default=0)),
                (
                    "bundle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="Papers.bundle"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="fixedpage",
            name="image",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="Papers.image",
            ),
        ),
        migrations.CreateModel(
            name="DiscardPage",
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
                ("discard_reason", models.TextField()),
                (
                    "image",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="Papers.image",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MobilePage",
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
                ("question_index", models.IntegerField()),
                ("version", models.IntegerField(default=None, null=True)),
                (
                    "image",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="Papers.image",
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
            model_name="fixedpage",
            name="paper",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="Papers.paper"
            ),
        ),
        migrations.CreateModel(
            name="ReferenceImage",
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
                    "image_file",
                    models.ImageField(
                        height_field="height",
                        upload_to="reference_images",
                        width_field="width",
                    ),
                ),
                ("parsed_qr", models.JSONField(default=dict, null=True)),
                ("page_number", models.PositiveIntegerField()),
                ("version", models.PositiveIntegerField()),
                ("height", models.IntegerField(default=0)),
                ("width", models.IntegerField(default=0)),
                (
                    "source_pdf",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="Preparation.papersourcepdf",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="bundle",
            constraint=models.UniqueConstraint(
                condition=models.Q(("_is_system", True)),
                fields=("name", "hash"),
                name="unique_system_bundles",
            ),
        ),
    ]
