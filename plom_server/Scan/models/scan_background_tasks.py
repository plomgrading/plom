# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.db import models

from Base.models import HueyTaskTracker
from ..models import StagingBundle


class PagesToImagesHueyTask(HueyTaskTracker):
    """Manage the background task for converting PDF pages into images."""

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    completed_pages = models.PositiveIntegerField(default=0)


class ManageParseQR(HueyTaskTracker):
    """Manage the background parse-qr tasks."""

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    completed_pages = models.PositiveIntegerField(default=0)


class ParseQR(HueyTaskTracker):
    """Parse a page of QR codes in the background."""

    file_path = models.TextField(default="")
    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    page_index = models.PositiveIntegerField(null=True)
