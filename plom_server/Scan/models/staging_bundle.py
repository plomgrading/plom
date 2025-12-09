# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Aidan Murphy

from django.db import models
from django.contrib.auth.models import User


class StagingBundle(models.Model):
    """A user-uploaded bundle that isn't validated.

    Note: StagingBundles can be deleted.  In this case the associated
    StagingImages and BaseImages are automatically deleted. There is a
    potential catch: if StagingBundle is pushed, then a Bundle is created and
    the BaseImages are shared between the original StagingBundle and the new
    Bundle.  In this case, its not well-defined what happens if you try to
    delete the original StagingBundle and we generally don't allow that.

    TODO: document other fields.

    Fields:
        slug: an alternative to the filename that would otherwise not
            be acceptable for various reasons.
        user: a reference to the User that uploaded the bundle file.
        number_of_pages: how many pages this bundle has.  Older code
            initially allowed this to be unknown (None); currently
            we set it when creating a bundle, although a future change
            to avoid opening the PDF only in worker threads (Huey)
            might revisit that, so its still allowed to be None for now.
        has_page_images: this bundle has been processed to create
            StagingImages.
        has_qr_codes: the StagingImages of this bundle have been
            processed to read QR codes.
        time_to_make_page_images: overall seconds to convert from
            PDF to images, including IO overhead (wall-clock time).
        time_to_read_qr: seconds of wall-clock to read all QR codes.
    """

    def _staging_bundle_upload_path(self, filename):
        # save bundle as "//media/staging/bundles/username/bundle-id/filename"
        return "staging/bundles/{}/{}/{}".format(self.user.username, self.pk, filename)

    slug = models.TextField(default="")
    pdf_file = models.FileField(upload_to=_staging_bundle_upload_path)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    timestamp = models.FloatField(default=0)
    pdf_hash = models.CharField(null=False, max_length=64)
    number_of_pages = models.PositiveIntegerField(null=True)
    force_page_render = models.BooleanField(default=False)
    has_page_images = models.BooleanField(default=False)
    has_qr_codes = models.BooleanField(default=False)
    is_push_locked = models.BooleanField(default=False)
    pushed = models.BooleanField(default=False)
    time_of_last_update = models.DateTimeField(auto_now=True)
    time_to_make_page_images = models.FloatField(default=0.0)
    time_to_read_qr = models.FloatField(default=0.0)
