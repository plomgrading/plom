# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Aden Chan
# Copyright (C) 2025 Colin B. Macdonald

from django.db import models
from plom_server.Preparation.models import PaperSourcePDF


class ReferenceImage(models.Model):
    """An image of a particular page of the assessment source.

    A cached copy of the rendered PDF file.

    source_pdf: a link the pdf file from which this came.
    image_file: an abstraction of a file for the image.
    parsed_qr: we place dummy QR codes on the reference pages during
        rendering, using the same process as Plom's actual paper
        creation.  We can read this information back here.
    page_number: which page is this.
    version: which version is this.
    height: how many pixels high is the image.
    width: how many pixels wide is the image.

    Notes on deletion: when a ReferenceImage is deleted, it DOES NOT
    automatically clean-up underlying files from its ``image_file``.
    If you (a service) wants to do that, you must be careful about
    rollbacks: the situation to protect against is the existence of
    a ReferenceImage *without* its underlying ``image_file``.
    One way to do this is to delete the ReferenceImage in a durable
    atomic operation AND THEN (after the durable block is committed)
    call ``image_file.delete(save=False)``.  This is done e.g., in
    TODO: insert reference.

    Historical note: we tried doing the delete a ``post_delete`` signal
    but it runs *during* the atomic durable.
    """

    page_number = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)
    image_file = models.ImageField(
        null=False,
        upload_to="reference_images",
        # tell Django where to automagically store height/width info on save
        height_field="height",
        width_field="width",
    )
    parsed_qr = models.JSONField(default=dict, null=True)
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)
