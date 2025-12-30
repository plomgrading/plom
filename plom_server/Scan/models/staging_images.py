# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2025 Colin B. Macdonald

from django.core.exceptions import ValidationError
from django.db import models

from ..models import StagingBundle
from plom_server.Base.models import BaseImage


class StagingImage(models.Model):
    """An image of a scanned page that isn't validated.

    Note that bundle_order is the 1-indexed position of the image with the pdf.
    This contrasts with pymupdf (for example) for which pages are 0-indexed.

    Also note: staging bundles (and these associated staging images and base
    images) can be deleted by the user - hence the base images are
    cascade-deleted. However, if the staging bundle is pushed we do not allow
    the user to delete the associated staging bundle (and staging images, base
    images).

    Fields:
        image_type: a mandatory argument for what type of image this is.
            The values are an enum.  If you want them printed for humans,
            call `get_image_type_display()`.  StagingImages typically start
            as UNREAD and then change their `image_type` as they are classified
            either by machine or by human.
        bundle: which StagingBundle does this image belong to?
        bundle_order: this is the "PDF page" of the image: the position within
            the bundle it came from.  One might say "page" but we don't b/c
            of ambiguities: a "page" might mean a double-sided sheet of paper,
            and more importantly, QR-coded images have an associated `page_number`
            within the assessment.
        baseimage: an immutable underlying image, including the on-disc storage.
            These can be shared with other models, namely `Image` that are
            created when the StagingBundle is pushed.
        parsed_qr: some information about any QR codes found on the page.
        rotation: currently this only deals with 0, 90, 180, 270, -90.
            fractional rotations are handled elsewhere,
        pushed: whether this bundle has been "pushed", making it ready for
            marking and generally harder to change.
        discard_reason: if the image is of type DISCARD, this will give
            human-readable explanation, such as who discarded it and what
            it was before.  Should generally be empty if this StagingImage
            isn't discarded, or perhaps wasn't recently.
        error_reason: if the image is of type ERROR, this will give a
            human-readable error message.  Should generally be empty if this
            StagingImage isn't in error.
        paper_number: used by type KNOWN or EXTRA, undefined for other types.
            if KNOWN, then this *must* be non-None, and gives the paper number
            of the known image.
            if EXTRA, then it *could* be an integer or None.  None means that
            the extra page has not be assigned yet.  See also `question_idx_list`.
        page_number: used by type KNOWN, undefined for other types.  KNOWN
            images *must* have a non-None integer value.
        version: used by type KNOWN, undefined for other types.  KNOWN
            images *must* have a non-None integer value.
        question_idx_list: used by type EXTRA.  Note that the null/None semantics
            of JSON fields are complicated.  If you store a "JSON null" (e.g.,
            ``json.dumps(None)``) in this, its not well-defined what happens so don't
            do that.  For example, if you know `paper_number` but don't yet know
            the questions, set `obj.question_idx_list = None`.
            When you do know it, it can be a list of integers, or an empty list.
            Currently the empty list means the image is assigned to the "DNM"
            (do not mark) group.
        history: a somewhat human-readable log of actions done to this image.
            Each string should be separated by a semicolon `";"`.  This string
            can growth larger with repeated operations; if that becomes a performance
            problem, or if we want to add time-stamps etc, then we could add a new
            StagingImageEvent table.
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

    # self.get_image_type_display is automatically created
    image_type = models.TextField(
        choices=ImageTypeChoices.choices, null=False, blank=False
    )

    bundle = models.ForeignKey(StagingBundle, on_delete=models.CASCADE)
    # starts from 1 not zero.
    bundle_order = models.PositiveIntegerField(null=True, blank=True)
    # we do not protect the base image here, rather if the base image is
    # deleted (eg when user removes a bundle) then these staging images
    # should also be deleted via this cascade.
    baseimage = models.OneToOneField(BaseImage, on_delete=models.CASCADE)
    parsed_qr = models.JSONField(default=dict, null=True, blank=True)
    rotation = models.IntegerField(null=True, default=None, blank=True)
    pushed = models.BooleanField(default=False)
    # used by KNOWN/EXTRA
    paper_number = models.PositiveIntegerField(null=True, default=None, blank=True)
    # used by KNOWN
    page_number = models.PositiveIntegerField(null=True, default=None, blank=True)
    version = models.PositiveIntegerField(null=True, default=None, blank=True)
    # Used by EXTRA
    # https://docs.djangoproject.com/en/6.0/topics/db/queries/#storing-and-querying-for-none
    question_idx_list = models.JSONField(default=None, null=True, blank=True)
    # used for DISCARD
    discard_reason = models.TextField(default="", blank=True)
    # used for ERROR
    error_reason = models.TextField(default="", blank=True)
    history = models.TextField(blank=True, null=False, default="")

    def save(self, *args, **kwargs) -> None:
        """Override the built-in save to call our validation code.

        See for example:
        https://stackoverflow.com/questions/4441539/why-doesnt-djangos-model-save-call-full-clean

        Note that invariants are NOT enforced if you make bulk operations.
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Called by full_clean to check stuff about the class instance."""
        try:
            self._check_invariants()
        except (AssertionError, ValueError) as e:
            # passing a string adds to the NON_FIELD_ERRORS key
            raise ValidationError(str(e))

    def _check_invariants(self) -> None:
        """Check for various illegal combinations of fields in the StagingImage table.

        Raises:
            AssertionError: something illegal.
            ValueError: something unexpected (and illegal).
        """
        UNREAD = self.ImageTypeChoices.UNREAD
        KNOWN = self.ImageTypeChoices.KNOWN
        UNKNOWN = self.ImageTypeChoices.UNKNOWN
        EXTRA = self.ImageTypeChoices.EXTRA
        DISCARD = self.ImageTypeChoices.DISCARD
        ERROR = self.ImageTypeChoices.ERROR

        if self.image_type == UNREAD:
            # TODO: learn how unread pages work: almost everything blank?
            pass
        elif self.image_type == KNOWN:
            assert self.paper_number is not None, "KNOWN must have paper_number"
        elif self.image_type == UNKNOWN:
            assert self.paper_number is None, "UNKNOWN must not have paper_number"
            assert self.page_number is None, "UNKNOWN must not have page_number"
            assert self.version is None, "UNKNOWN must not have version"
        elif self.image_type == EXTRA:
            assert self.page_number is None, "EXTRA must not have page_number"
            assert self.version is None  # ?
        elif self.image_type == DISCARD:
            assert self.discard_reason, "DISCARD must have discard_reason"
        elif self.image_type == ERROR:
            assert self.error_reason, "ERROR must have error_reason"
        else:
            raise ValueError("Unexpected value for enum")

        # TODO: what about these fields?
        # parsed_qr
        # rotation
        # pushed

        # And a pass over the fields
        if self.paper_number is not None:
            assert self.image_type in (KNOWN, EXTRA)
        if self.page_number is not None:
            assert self.image_type == KNOWN
        if self.version is not None:
            assert self.image_type == KNOWN
        if self.question_idx_list is not None:
            assert self.image_type == EXTRA
            # for now you must know both question_idx_list and paper_number
            # but this could change in the future.
            assert self.paper_number is not None
        if self.discard_reason:
            assert self.image_type == DISCARD
        if self.error_reason:
            assert self.image_type == ERROR


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
