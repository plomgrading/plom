# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.db import models

from Base.models import BaseHueyTask
from ..models import StagingBundle


class ManagePageToImage(BaseHueyTask):
    """Manage the background PDF page into an image tasks."""

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    completed_pages = models.PositiveIntegerField(default=0)


class PageToImage(BaseHueyTask):
    """Convert a PDF page into an image in the background."""

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)


class ManageParseQR(BaseHueyTask):
    """Manage the background parse-qr tasks."""

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    completed_pages = models.PositiveIntegerField(default=0)


class ParseQR(BaseHueyTask):
    """Parse a page of QR codes in the background."""

    file_path = models.TextField(default="")
    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    page_index = models.PositiveIntegerField(null=True)
