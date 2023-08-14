# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

import pathlib
from pathlib import Path
from typing import Union

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from Base.models import HueyTask
from Papers.models import Paper


class ReassembleTask(HueyTask):
    paper = models.OneToOneField(Paper, null=False, on_delete=models.CASCADE)
    pdf_file = models.FileField(upload_to="papersToPrint/", null=True)

    def __str__(self):
        """Stringify task using its related test-paper's number."""
        return "Task Object " + str(self.paper.paper_number)

    def unlink_associated_pdf(self):
        print(
            f"Deleting reassembled pdf associated with paper {self.paper.paper_number} if it exists"
        )
        f = self.file_path()
        if not f:
            print(f"  But no file associated with paper {self.paper.paper_number}")
            return
        f.unlink(missing_ok=True)

    def file_path(self) -> Union[pathlib.Path, None]:
        """Get the path of the generated PDF file.

        Returns:
            If the file exists, return the path. If it doesn't, return `None`.
        """
        if not self.pdf_file:
            return None
        return Path(self.pdf_file.path)


@receiver(pre_delete, sender=Paper)
def ReassembleTask_delete_associated_file(sender, instance, using, **kwargs):
    if hasattr(instance, "reassembletask"):
        instance.reassembletask.unlink_associated_pdf()
