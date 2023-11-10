# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Julian Lapenna

from django.db import models
from django.contrib.auth.models import User

from Scan.models import StagingBundle


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
        In the future this could be a url to some cloud storage.
    hash (str): the sha256 hash of the image.
    rotation (int): the angle to rotate the original image in order to give
        it the correct orientation.
    parsed_qr (dict): the JSON dict containing QR code information for the page image.
    height (int): the height of the image in px (auto-populated on save)
    width (int): the width of the image in px (auto-populated on save)
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
    image_file = models.ImageField(
        null=False,
        upload_to=_image_upload_path,
        height_field="height",
        width_field="width",
    )
    hash = models.CharField(null=True, max_length=64)
    rotation = models.IntegerField(null=False, default=0)
    parsed_qr = models.JSONField(default=dict, null=True)

    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)


class DiscardPage(models.Model):
    image = models.OneToOneField(Image, null=True, on_delete=models.CASCADE)
    discard_reason = models.TextField()
