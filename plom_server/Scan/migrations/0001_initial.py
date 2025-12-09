import django.db.models.deletion
import plom_server.Scan.models.staging_bundle
import plom_server.Scan.models.staging_images
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("Base", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StagingImage",
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
                    "image_type",
                    models.TextField(
                        choices=[
                            ("UNREAD", "Unread"),
                            ("KNOWN", "Known"),
                            ("UNKNOWN", "Unknown"),
                            ("EXTRA", "Extra"),
                            ("DISCARD", "Discard"),
                            ("ERROR", "Error"),
                        ]
                    ),
                ),
                ("bundle_order", models.PositiveIntegerField(null=True)),
                ("parsed_qr", models.JSONField(default=dict, null=True)),
                ("rotation", models.IntegerField(default=None, null=True)),
                ("pushed", models.BooleanField(default=False)),
                ("paper_number", models.PositiveIntegerField(default=None, null=True)),
                ("page_number", models.PositiveIntegerField(default=None, null=True)),
                ("version", models.PositiveIntegerField(default=None, null=True)),
                ("question_idx_list", models.JSONField(default=None, null=True)),
                ("discard_reason", models.TextField(default="")),
                ("error_reason", models.TextField(default="")),
                (
                    "baseimage",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="Base.baseimage"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="StagingBundle",
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
                ("slug", models.TextField(default="")),
                (
                    "pdf_file",
                    models.FileField(
                        upload_to=plom_server.Scan.models.staging_bundle.StagingBundle._staging_bundle_upload_path
                    ),
                ),
                ("timestamp", models.FloatField(default=0)),
                ("pdf_hash", models.CharField(max_length=64)),
                ("number_of_pages", models.PositiveIntegerField(null=True)),
                ("force_page_render", models.BooleanField(default=False)),
                ("has_page_images", models.BooleanField(default=False)),
                ("has_qr_codes", models.BooleanField(default=False)),
                ("is_push_locked", models.BooleanField(default=False)),
                ("pushed", models.BooleanField(default=False)),
                ("time_of_last_update", models.DateTimeField(auto_now=True)),
                ("time_to_make_page_images", models.FloatField(default=0.0)),
                ("time_to_read_qr", models.FloatField(default=0.0)),
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
            name="PagesToImagesChore",
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
                ("completed_pages", models.PositiveIntegerField(default=0)),
                (
                    "bundle",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="Scan.stagingbundle",
                    ),
                ),
            ],
            bases=("Base.hueytasktracker",),
        ),
        migrations.CreateModel(
            name="ManageParseQRChore",
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
                ("completed_pages", models.PositiveIntegerField(default=0)),
                (
                    "bundle",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="Scan.stagingbundle",
                    ),
                ),
            ],
            bases=("Base.hueytasktracker",),
        ),
        migrations.CreateModel(
            name="StagingThumbnail",
            fields=[
                (
                    "staging_image",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        serialize=False,
                        to="Scan.stagingimage",
                    ),
                ),
                (
                    "image_file",
                    models.ImageField(
                        upload_to=plom_server.Scan.models.staging_images.StagingThumbnail._staging_thumbnail_upload_path
                    ),
                ),
                ("time_of_last_update", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name="stagingimage",
            name="bundle",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="Scan.stagingbundle"
            ),
        ),
    ]
