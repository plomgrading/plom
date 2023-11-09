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

from Base.models import BaseHueyTaskTracker
from Papers.models import Paper


class PDFHueyTask(BaseHueyTaskTracker):
    # OneToOneField makes a field called "pdfhueytask" in the Paper table
    paper = models.OneToOneField(Paper, null=False, on_delete=models.CASCADE)
    pdf_file = models.FileField(upload_to="papersToPrint/", null=True)
    student_name = models.TextField(default=None, null=True)
    student_id = models.TextField(default=None, null=True)

    # Note that the cascade-delete does not call PDFHueyTask's delete
    # function, instead use the pre_delete signal to call a function
    # to unlink the associated file
    # See - https://docs.djangoproject.com/en/4.1/ref/models/fields/#django.db.models.CASCADE

    def __str__(self):
        """Stringify task using its related test-paper's number."""
        return "Task Object " + str(self.paper.paper_number)

    def unlink_associated_pdf(self):
        print(
            f"Deleting pdf associated with paper {self.paper.paper_number} if it exists"
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

    def file_display_name(self):
        """Return a file name for displaying on the PDF builder GUI."""
        if self.student_id:
            return f"exam_{self.paper.paper_number:04}_{self.student_id}.pdf"
        else:
            return f"exam_{self.paper.paper_number:04}.pdf"


@receiver(pre_delete, sender=Paper)
def PDFHueyTask_delete_associated_file(sender, instance, using, **kwargs):
    # if the paper has a pdf task then delete it.
    # we need this check or a try-except - see https://docs.djangoproject.com/en/4.1/topics/db/examples/one_to_one/
    if hasattr(instance, "pdfhueytask"):
        instance.pdfhueytask.unlink_associated_pdf()
