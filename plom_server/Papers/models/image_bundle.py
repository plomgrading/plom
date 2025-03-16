# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2025 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna

from django.db import models
from django.db.models.query_utils import Q
from django.contrib.auth.models import User

from plom_server.Scan.models import StagingBundle
from plom_server.Base.models import BaseImage


class Bundle(models.Model):
    """Table to store information on the bundle (pdf) that a given uploaded image comes from.

    Notice that this does not include a ref to the bundle-file - since
    we are not(?) intending to store the bundle itself after
    processing.

    name (str): The name of the pdf/bundle (ie just the stem of the
        bundle's path)
    pdf_hash (str): Generally the sha256 of the bundle/pdf file, although
        special cases it could be something else (e.g., there is special
        bundle for substitute pages in ForgiveMissingService.py)
    _is_system: if the bundle is a system bundle then allow one bundle
        with this precise name and hash. This is used internally, but
        not currently used to prevent duplicate uploads.
    user: The user who pushed the bundle.
    time_of_last_update (datetime): The time of last change to the bundle.
    staging_bundle: a key to the staging bundle from which this bundle was created by a push
    """

    name = models.TextField(null=False)
    pdf_hash = models.CharField(null=False, max_length=64)
    _is_system = models.BooleanField(default=False)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time_of_last_update = models.DateTimeField(auto_now=True)
    staging_bundle = models.ForeignKey(
        StagingBundle, null=True, on_delete=models.SET_NULL
    )

    class Meta:
        constraints = [
            # Check that each name-pdf_hash pair is unique, when is_system is set
            models.UniqueConstraint(
                fields=["name", "pdf_hash"],
                condition=Q(_is_system=True),
                name="unique_system_bundles",
            ),
        ]


class Image(models.Model):
    """Table to store information about an uploaded page-image.

    bundle (ref to Bundle object): which bundle the image is from
    bundle_order (int): the position of the image in that bundle
        (ie which page in the pdf/bundle) - is 1-indexed and not 0-indexed
    original_name (str): the name of the image-file when it was extracted
        from the bundle. Typically, this will be something like "foo-7.png",
        which also indicates that it was page-7 from the bundle foo.pdf"

    baseimage (BaseImage): a key to the underlying base-image (which stores
        the file, hash and other information.

    rotation (int): the angle to rotate the original image in order to give
        it the correct approximate orientation.  Currently this only deals
        with 0, 90, 180, 270, -90.  More precise fractional rotations are
        handled elsewhere,

    parsed_qr (dict): the JSON dict containing QR code information for the page image.

    """

    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    bundle_order = models.PositiveIntegerField(null=True)
    original_name = models.TextField(null=True)  # can be empty.
    baseimage = models.ForeignKey(BaseImage, on_delete=models.PROTECT)
    rotation = models.IntegerField(null=False, default=0)
    parsed_qr = models.JSONField(default=dict, null=True)


class DiscardPage(models.Model):
    image = models.ForeignKey(Image, null=True, on_delete=models.CASCADE)
    discard_reason = models.TextField()
