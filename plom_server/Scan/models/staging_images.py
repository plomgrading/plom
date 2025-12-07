# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2025 Colin B. Macdonald

from django.db import models

from ..models import StagingBundle
from plom_server.Base.models import BaseImage


class StagingImage(models.Model):
    """An image of a scanned page that isn't validated.

    Note that bundle_order is the 1-indexed position of the image with the pdf. This contrasts with pymupdf (for example) for which pages are 0-indexed.

    Also note: staging bundles (and these associated staging images and base
    images) can be deleted by the user - hence the base images are
    cascade-deleted. However, if the staging bundle is pushed we do not allow
    the user to delete the associated staging bundle (and staging images, base
    images).

    TODO: document other fields.

    Fields:
        rotation: currently this only deals with 0, 90, 180, 270, -90.
            fractional rotations are handled elsewhere,
        discard_reason: if the image is of type DISCARD, this will give
            human-readable explanation, such as who discarded it and what
            it was before.  Should generally be empty if this StagingImage
            isn't discarded, or perhaps wasn't recently.
    """

    # some implicit constructor is generating pylint errors:
    # pylint: disable=too-many-function-args
    ImageTypeChoices = models.TextChoices(
        "ImageType", "UNREAD KNOWN UNKNOWN EXTRA DISCARD ERROR"
    )
    UNREAD = ImageTypeChoices.UNREAD
    KNOWN = ImageTypeChoices.KNOWN
    UNKNOWN = ImageTypeChoices.UNKNOWN
    EXTRA = ImageTypeChoices.EXTRA
    DISCARD = ImageTypeChoices.DISCARD
    ERROR = ImageTypeChoices.ERROR

    bundle = models.ForeignKey(StagingBundle, on_delete=models.CASCADE)
    # starts from 1 not zero.
    bundle_order = models.PositiveIntegerField(null=True)
    # we do not protect the base image here, rather if the base image is
    # deleted (eg when user removes a bundle) then these staging images
    # should also be deleted via this cascade.
    baseimage = models.OneToOneField(BaseImage, on_delete=models.CASCADE)
    parsed_qr = models.JSONField(default=dict, null=True)
    rotation = models.IntegerField(null=True, default=None)
    pushed = models.BooleanField(default=False)
    image_type = models.TextField(choices=ImageTypeChoices.choices, default=UNREAD)
    discard_reason = models.TextField(default="")


class StagingThumbnail(models.Model):
    def _staging_thumbnail_upload_path(self, filename):
        # save thumbnail in "//media/staging/bundles/username/bundle-pk/page_images/filename"
        return "staging/bundles/{}/{}/page_images/{}".format(
            self.staging_image.bundle.user.username,
            self.staging_image.bundle.pk,
            filename,
        )

    staging_image = models.OneToOneField(
        StagingImage, on_delete=models.CASCADE, primary_key=True
    )
    image_file = models.ImageField(upload_to=_staging_thumbnail_upload_path)
    time_of_last_update = models.DateTimeField(auto_now=True)


class KnownStagingImage(models.Model):
    staging_image = models.OneToOneField(
        StagingImage, primary_key=True, on_delete=models.CASCADE
    )
    paper_number = models.PositiveIntegerField(null=False)
    page_number = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)


class ExtraStagingImage(models.Model):
    staging_image = models.OneToOneField(
        StagingImage, primary_key=True, on_delete=models.CASCADE
    )
    paper_number = models.PositiveIntegerField(null=True, default=None)
    # https://docs.djangoproject.com/en/4.1/topics/db/queries/#storing-and-querying-for-none
    question_idx_list = models.JSONField(default=None, null=True)


class ErrorStagingImage(models.Model):
    staging_image = models.OneToOneField(
        StagingImage, primary_key=True, on_delete=models.CASCADE
    )
    error_reason = models.TextField()
