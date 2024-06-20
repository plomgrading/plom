# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Aden Chan

from pathlib import Path
from django.db import models
from django.dispatch import receiver
from Preparation.models import PaperSourcePDF


class ReferenceImage(models.Model):
    source_pdf = models.ForeignKey(PaperSourcePDF, null=False, on_delete=models.CASCADE)
    image_file = models.ImageField(
        null=False,
        upload_to="reference_images",
        # tell Django where to automagically store height/width info on save
        height_field="height",
        width_field="width",
    )
    parsed_qr = models.JSONField(default=dict, null=True)
    page_number = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)


@receiver(models.signals.post_delete, sender=ReferenceImage)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding `ReferenceImage` object is deleted.
    """
    if instance.image_file:
        with Path(instance.image_file.path) as path:
            if path.is_file():
                path.unlink()
