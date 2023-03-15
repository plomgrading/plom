# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu

from django.db import models
from django.contrib.auth.models import User

from Base.models import HueyTask


class StagingBundle(models.Model):
    """
    A user-uploaded bundle that isn't validated.
    """

    slug = models.TextField(default="")
    file_path = models.TextField(default="")
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    timestamp = models.FloatField(default=0)
    pdf_hash = models.CharField(null=False, max_length=64)
    has_page_images = models.BooleanField(default=False)
    has_qr_codes = models.BooleanField(default=False)
    pushed = models.BooleanField(default=False)


class StagingImage(models.Model):
    """
    An image of a scanned page that isn't validated.
    """

    bundle = models.ForeignKey(StagingBundle, on_delete=models.CASCADE)
    bundle_order = models.PositiveIntegerField(null=True)
    file_name = models.TextField(default="")
    file_path = models.TextField(default="")
    image_hash = models.CharField(max_length=64)
    parsed_qr = models.JSONField(default=dict, null=True)
    paper_id = models.PositiveIntegerField(default=None, null=True)
    page_number = models.PositiveIntegerField(default=None, null=True)
    rotation = models.IntegerField(default=0)
    pushed = models.BooleanField(default=False)
    colliding = models.BooleanField(default=False)
    unknown = models.BooleanField(default=False)
    error = models.BooleanField(default=False)
    flagged = models.BooleanField(default=False)


class DiscardedStagingImage(models.Model):
    """
    An image of a discarded page.
    """

    bundle = models.ForeignKey(StagingBundle, on_delete=models.CASCADE)
    bundle_order = models.PositiveIntegerField(null=True)
    file_name = models.TextField(default="")
    file_path = models.TextField(default="")
    image_hash = models.CharField(max_length=64)
    parsed_qr = models.JSONField(default=dict, null=True)
    rotation = models.IntegerField(default=0)
    restore_class = models.TextField(null=False, default="")


class CollisionStagingImage(models.Model):
    """
    An image of a collision page.
    """

    bundle = models.ForeignKey(StagingBundle, on_delete=models.CASCADE)
    bundle_order = models.PositiveIntegerField(null=True)
    file_name = models.TextField(default="")
    file_path = models.TextField(default="")
    image_hash = models.CharField(max_length=64)
    parsed_qr = models.JSONField(default=dict, null=True)
    rotation = models.IntegerField(default=0)
    paper_number = models.PositiveIntegerField(null=True)
    page_number = models.PositiveIntegerField(null=True)
    version_number = models.PositiveIntegerField(null=True)


class UnknownStagingImage(models.Model):
    """
    An image of an unknown page.
    """

    bundle = models.ForeignKey(StagingBundle, on_delete=models.CASCADE)
    bundle_order = models.PositiveIntegerField(null=True)
    file_name = models.TextField(default="")
    file_path = models.TextField(default="")
    image_hash = models.CharField(max_length=64)
    rotation = models.IntegerField(default=0)


class PageToImage(HueyTask):
    """
    Convert a PDF page into an image in the background.
    """

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)


class ParseQR(HueyTask):
    """
    Parse a page of QR codes in the background.
    """

    file_path = models.TextField(default="")
    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    page_index = models.PositiveIntegerField(null=True)
