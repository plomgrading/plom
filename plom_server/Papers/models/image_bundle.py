# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna

from django.db import models
from django.contrib.auth.models import User

from plom_server.Scan.models import StagingBundle


class Bundle(models.Model):
    """Table to store information on the bundle (pdf) that a given uploaded image comes from.

    Notice that this does not include a ref to the bundle-file - since
    we are not(?) intending to store the bundle itself after
    processing.

    name (str): The name of the pdf/bundle (ie just the stem of the
        bundle's path)
    hash (str): The sha256 of the bundle/pdf file.
    user: The user who pushed the bundle.
    time_of_last_update (datetime): The time of last change to the bundle.
    staging_bundle: a key to the staging bundle from which this bundle was created by a push
    """

    name = models.TextField(null=False)
    hash = models.CharField(null=False, max_length=64)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time_of_last_update = models.DateTimeField(auto_now=True)
    staging_bundle = models.ForeignKey(
        StagingBundle, null=True, on_delete=models.SET_NULL
    )


class Image(models.Model):
    """Table to store information about an uploaded page-image.

    bundle (ref to Bundle object): which bundle the image is from
    bundle_order (int): the position of the image in that bundle
        (ie which page in the pdf/bundle) - is 1-indexed and not 0-indexed
    original_name (str): the name of the image-file when it was extracted
        from the bundle. Typically, this will be something like "foo-7.png",
        which also indicates that it was page-7 from the bundle foo.pdf"
    image_file (ImageField): the django-imagefield storing the image for the server.
        In the future this could be a url to some cloud storage. Note that this also
        tells django where to automagically compute+store height/width information on save
    hash (str): the sha256 hash of the image.
    rotation (int): the angle to rotate the original image in order to give
        it the correct approximate orientation.  Currently this only deals
        with 0, 90, 180, 270, -90.  More precise fractional rotations are
        handled elsewhere,

    parsed_qr (dict): the JSON dict containing QR code information for the page image.

    height (int): the height of the image in px (auto-populated on
        save by django). Note that this height is the *raw* height in
        pixels before any exif rotations and any plom rotations.

    width (int): the width of the image in px (auto-populated on
        save by django).  Note that this width is the *raw* width in
        pixels before any exif rotations and any plom rotations.
    """

    def _image_upload_path(self, filename: str) -> str:
        """Create a path to which the associated file should be saved.

        Given a image instance and a filename create a path to which
        the associated file should be saved. We use this function to set
        save-paths for pushed images rather than 'hand-coding' them
        elsewhere.

        Args:
            filename: the name of the file to be saved at the created path.

        Returns:
            The string of the path to which the image file
            will be saved (relative to the media directory, and including the
            actual filename).
        """
        return f"pushed_images/{self.bundle.pk:05}/{filename}"

    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    bundle_order = models.PositiveIntegerField(null=True)
    original_name = models.TextField(null=True)  # can be empty.
    # using imagefield over filefield allows django to automagically compute
    # height and width of the image - see django docs.
    image_file = models.ImageField(
        null=False,
        upload_to=_image_upload_path,
        # tell Django where to automagically store height/width info on save
        height_field="height",
        width_field="width",
    )
    hash = models.CharField(null=True, max_length=64)
    rotation = models.IntegerField(null=False, default=0)
    parsed_qr = models.JSONField(default=dict, null=True)

    # height and width fields auto-populated by django on save
    # I don't think we use these *yet* but we may in the future
    # These are raw height/width in pixels before any exif rotations or plom rotations.
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)


class DiscardPage(models.Model):
    image = models.ForeignKey(Image, null=True, on_delete=models.CASCADE)
    discard_reason = models.TextField()
