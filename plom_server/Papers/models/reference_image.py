# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2025 Colin B. Macdonald

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
    """Deletes file when linked `ReferenceImage` object is deleted."""
    if instance.image_file:
        path = Path(instance.image_file.path)
        if path.is_file():
            # unclear what happens if this fails: object is already deleted
            path.unlink()
