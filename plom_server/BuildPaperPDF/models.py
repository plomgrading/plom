# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

import pathlib
from pathlib import Path
from typing import Union

from django.db import models

# from django.db.models.signals import pre_delete

from Base.models import HueyTaskTracker
from Papers.models import Paper


class BuildPaperPDFChore(HueyTaskTracker):
    """Represents the chore of building a PDF file for each paper."""

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    pdf_file = models.FileField(upload_to="papersToPrint/", null=True)
    display_filename = models.TextField(null=True)
    # only used for UI display, but also a record of what was on the PDF file
    student_name = models.TextField(default=None, null=True)
    student_id = models.TextField(default=None, null=True)

    # Note that the cascade-delete does not call our delete
    # function, instead use the pre_delete signal to unlink the associated file
    # See - https://docs.djangoproject.com/en/4.1/ref/models/fields/#django.db.models.CASCADE
    # TODO: we removed this.

    def __str__(self):
        """Stringify task using its related test-paper's number."""
        return "Task Object " + str(self.paper.paper_number)

    def unlink_associated_pdf(self):
        print(
            f"Deleting pdf associated with paper {self.paper.paper_number} if it exists"
        )
        if self.pdf_file is None:
            print(f"  But no file associated with paper {self.paper.paper_number}")
            return
        self.pdf_file.path.unlink(missing_ok=True)
