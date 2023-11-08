# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2023 Colin B. Macdonald

from django.db import models

from Base.models import BaseHueyTask
from Scan.models import StagingImage


class CreatePaperHueyTask(BaseHueyTask):
    """Create a test-paper and save its structure to the database."""

    paper_number = models.PositiveIntegerField(null=False, unique=True)


class CreateImageHueyTask(BaseHueyTask):
    """Create an image by copying a validated StagingImage instance."""

    staging_image = models.ForeignKey(
        StagingImage, null=True, on_delete=models.SET_NULL
    )
