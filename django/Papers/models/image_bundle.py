# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Andrew Rechnitzer
# Copyright (C) 2022-2023 Edith Coates

from django.db import models
from polymorphic.models import PolymorphicModel


class Bundle(models.Model):
    """Table to store information on the bundle (pdf) that a given
    uploaded image comes from.

    Notice that this does not include a ref to the bundle-file - since
    we are not(?) intending to store the bundle itself after
    processing.

    name (str): The name of the pdf/bundle (ie just the stem of the
        bundle's path)
    hash (str): The sha256 of the bundle/pdf file.

    """

    name = models.TextField(null=False)
    hash = models.CharField(null=False, max_length=64)


# TODO - remove polymorphism here and delete older image types no longer used.


class Image(PolymorphicModel):
    """Table to store information about an uploaded page-image.

    bundle (ref to Bundle object): which bundle the image is from
    bundle_order (int): the position of the image in that bundle
        (ie which page in the pdf/bundle)
    original_name (str): the name of the image-file when it was extracted
        from the bundle. Typically, this will be something like "foo-7.png",
        which also indicates that it was page-7 from the bundle foo.pdf"
    file_name (Path): the path to where the image is stored by the server.
        In the future this could be a url to some cloud storage.
    hash (str): the sha256 hash of the image.
    rotation (int): the angle to rotate the original image in order to give
        it the correct orientation.
    """

    bundle = models.ForeignKey(Bundle, on_delete=models.CASCADE)
    bundle_order = models.PositiveIntegerField(null=True)
    original_name = models.TextField(null=True)  # can be empty.
    file_name = models.TextField(null=False)
    hash = models.CharField(null=True, max_length=64)
    rotation = models.IntegerField(null=False, default=0)


# TODO - rename this class
class DImage(models.Model):
    image = models.ForeignKey(Image, null=True, on_delete=models.CASCADE)
    discard_reason = models.TextField()


# TODO - remove the classes below.


class CollidingImage(Image):
    """Table to store information about colliding page-images.

    Fields:
        paper_number (int): test-paper ID
        page_number (int): index of page
    """

    paper_number = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField()


class DiscardedImage(Image):
    """
    Table to store information about discarded page-images.

    Fields:
        restore_class (str): the name of the class that this image would be restored to.
        restore_fields (dict): Extra fields to populate when restoring the image. For example, it
            would contain the "paper_number" and "page_number" fields of a discarded colliding-image.
    """

    restore_class = models.TextField(null=False, default="")
    restore_fields = models.JSONField(null=False, default=dict)


class ErrorImage(Image):
    """
    Table to store information about error page-images.

    Args:
        paper_number (int): test-paper ID
        page_number (int): index of page
        version_number (int): version of page
        flagged (bool): send to manager or not
        comment (str): scanner message to manager
    """

    paper_number = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField()
    version_number = models.PositiveIntegerField()
    flagged = models.BooleanField(default=False)
    comment = models.TextField(default="", null=True)
