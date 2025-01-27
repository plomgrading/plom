# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

from django.db import models
from django.contrib.auth.models import User


class StagingBundle(models.Model):
    """A user-uploaded bundle that isn't validated.

    TODO: document other fields.

    Fields:
        number_of_pages: how many pages this bundle has.  Initially
            this can be unknown (None); in that case, when we start
            processing the bundle, it will be set.  Optionally, if
            you know this initially you can set it *before* the
            processing has started.  TODO: I might remove that!
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
