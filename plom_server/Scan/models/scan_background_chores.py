# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.db import models

from Base.models import HueyTaskTracker
from ..models import StagingBundle


class PagesToImagesChore(HueyTaskTracker):
    """Manage the background chore (Huey Task) for converting PDF pages into images."""

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    completed_pages = models.PositiveIntegerField(default=0)


class ManageParseQRChore(HueyTaskTracker):
    """Manage the background chore (Huey Task) to parse QR codes from images."""

    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    completed_pages = models.PositiveIntegerField(default=0)


# TODO: do we need this or can I use a plain ol HueyTaskTracker?
# It is currently unused: if we keep it, rename to ParseQRChore
class ParseQR(HueyTaskTracker):
    """Parse a page of QR codes in the background."""

    file_path = models.TextField(default="")
    bundle = models.ForeignKey(StagingBundle, null=True, on_delete=models.CASCADE)
    page_index = models.PositiveIntegerField(null=True)
