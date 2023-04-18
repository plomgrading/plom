# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

from django.db import models
from django.contrib.auth.models import User

from Base.models import HueyTask


def staging_bundle_upload_path(instance, filename):
    # save bundle as "media/bundles/username/timestamp/filename.pdf"
    return "{}/bundles/{}/{}".format(
        instance.user.username, instance.timestamp, filename
    )


def staging_image_upload_path(instance, filename):
    # save bundle-images as "media/bundles/username/timestamp/pageImages/filename"
    return "{}/bundles/{}/pageImages/{}".format(
        instance.bundle.user.username, instance.bundle.timestamp, filename
    )


class StagingBundle(models.Model):
    """
    A user-uploaded bundle that isn't validated.
    """

    slug = models.TextField(default="")
    pdf_file = models.FileField(upload_to=staging_bundle_upload_path)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    timestamp = models.FloatField(default=0)
    pdf_hash = models.CharField(null=False, max_length=64)
    number_of_pages = models.PositiveIntegerField(null=True)
    has_page_images = models.BooleanField(default=False)
    has_qr_codes = models.BooleanField(default=False)
    pushed = models.BooleanField(default=False)


class StagingImage(models.Model):
    """
    An image of a scanned page that isn't validated.
    """

    bundle = models.ForeignKey(StagingBundle, on_delete=models.CASCADE)
    bundle_order = models.PositiveIntegerField(null=True)
    image_file = models.ImageField(upload_to=staging_image_upload_path)
    image_hash = models.CharField(max_length=64)
    parsed_qr = models.JSONField(default=dict, null=True)
    paper_id = models.PositiveIntegerField(default=None, null=True)
    page_number = models.PositiveIntegerField(default=None, null=True)
    rotation = models.IntegerField(default=0)
    pushed = models.BooleanField(default=False)
    image_type = models.CharField(default="unread", max_length=16)


class KnownStagingImage(models.Model):
    staging_image = models.OneToOneField(
        StagingImage, primary_key=True, on_delete=models.CASCADE
    )
    paper_number = models.PositiveIntegerField(null=False)
    page_number = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)


class ExtraStagingImage(models.Model):
    # NOTE - we must have that paper_number and question_list are **both** null or both filled.

    staging_image = models.OneToOneField(
        StagingImage, primary_key=True, on_delete=models.CASCADE
    )
    paper_number = models.PositiveIntegerField(null=True, default=None)
    # https://docs.djangoproject.com/en/4.1/topics/db/queries/#storing-and-querying-for-none
    question_list = models.JSONField(default=None, null=True)
    # by default we store a null json field - this makes it easier to query
    # whether the extra page has data or not.


class UnknownStagingImage(models.Model):
    staging_image = models.OneToOneField(
        StagingImage, primary_key=True, on_delete=models.CASCADE
    )


class DiscardStagingImage(models.Model):
    staging_image = models.OneToOneField(
        StagingImage, primary_key=True, on_delete=models.CASCADE
    )
    discard_reason = models.TextField()


class ErrorStagingImage(models.Model):
    staging_image = models.OneToOneField(
        StagingImage, primary_key=True, on_delete=models.CASCADE
    )
    error_reason = models.TextField()


class ManagePageToImage(HueyTask):
    """
    Manage the background PDF page into an image tasks
    """

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    completed_pages = models.PositiveIntegerField(default=0)


class PageToImage(HueyTask):
    """
    Convert a PDF page into an image in the background.
    """

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)


class ManageParseQR(HueyTask):
    """
    Manage the background parse-qr tasks
    """

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    completed_pages = models.PositiveIntegerField(default=0)


class ParseQR(HueyTask):
    """
    Parse a page of QR codes in the background.
    """

    file_path = models.TextField(default="")
    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    page_index = models.PositiveIntegerField(null=True)
