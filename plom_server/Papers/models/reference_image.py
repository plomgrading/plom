# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2025 Colin B. Macdonald

from django.db import models
from django.dispatch import receiver
from plom_server.Preparation.models import PaperSourcePDF


class ReferenceImage(models.Model):
    """An image of a particular page of the assessment source.

    A cached copy of the rendered PDF file.

    source_pdf: a link the pdf file from which this came.
    image: an abstraction of a file for the image.
    parsed_qr: TODO that is this?  Source PDF shouldn't have
        any QR codes so why does this and what is it for?
    page_number: which page is this.
    version: which version is this.
    height: how many pixels high is the image.
    width: how many pixels wide is the image.
    """

    # this on_delete means that when PaperSourcePDF is deleted, these ReferenceImages
    # will also be deleted automatically
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
    """Deletes file when linked `ReferenceImage` object is deleted.

    Note: we must be careful about rollbacks caused by an upstream atomic
    transaction in a function outside of where the deletion happens (even
    if that function itself is atomic).

    Django docs do say this:

        Note that the object will no longer be in the database,
        so be very careful what you do with this instance.

    So perhaps its enough that you use a durable transaction on the
    code that triggers the deletion.
    """
    if instance.image_file:
        # https://docs.djangoproject.com/en/5.1/ref/models/fields/#django.db.models.fields.files.FieldFile.delete
        # Seems no exception raises if the file has already been deleted
        # (e.g., accidentally), tested March 2025 using local file storage
        instance.image_file.delete(save=False)
