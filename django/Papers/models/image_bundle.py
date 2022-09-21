from django.db import models


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


class Image(models.Model):
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
    file_name = models.ImageField(upload_to="images/", null=False)
    hash = models.CharField(null=True, max_length=64)
    rotation = models.IntegerField(null=False, default=0)


# TODO Add unknown-image, discarded-image and annotation-image
