# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer

from django.db import models
from django.contrib.auth.models import User


class StagingBundle(models.Model):
    """A user-uploaded bundle that isn't validated."""

    def _staging_bundle_upload_path(self, filename):
        # save bundle as "//media/staging/bundles/username/bundle-timestamp/filename"
        return "staging/bundles/{}/{}/{}".format(
            self.user.username, self.timestamp, filename
        )

    slug = models.TextField(default="")
    pdf_file = models.FileField(upload_to=_staging_bundle_upload_path)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    timestamp = models.FloatField(default=0)
    pdf_hash = models.CharField(null=False, max_length=64)
    number_of_pages = models.PositiveIntegerField(null=True)
    has_page_images = models.BooleanField(default=False)
    has_qr_codes = models.BooleanField(default=False)
    is_mid_push = models.BooleanField(default=False)
    pushed = models.BooleanField(default=False)
    time_of_last_update = models.DateTimeField(auto_now=True)
