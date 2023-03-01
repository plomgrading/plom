# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver

from Base.models import HueyTask
from Papers.models import Paper

from pathlib import Path


class PDFTask(HueyTask):
    paper = models.OneToOneField(Paper, null=False, on_delete=models.CASCADE)
    pdf_file = models.FileField(upload_to="papersToPrint/", null=True)
    student_name = models.TextField(default=None, null=True)
    student_id = models.TextField(default=None, null=True)

    # Note that the cascade-delete does not call PDFTask's delete
    # function, instead use the pre_delete signal to call a function
    # to unlink the associated file
    # See - https://docs.djangoproject.com/en/4.1/ref/models/fields/#django.db.models.CASCADE

    def __str__(self):
        return "Task Object " + str(self.paper_number)

    def unlink_associated_pdf(self):
        print(
            f"Deleting pdf associated with paper {self.paper.paper_number} if it exists"
        )
        self.file_path().unlink(missing_ok=True)

    def file_path(self):
        return Path(self.pdf_file.path)


@receiver(pre_delete, sender=Paper)
def PDFTask_delete_associated_file(sender, instance, using, **kwargs):
    if instance.pdftask:
        instance.pdftask.unlink_associated_pdf()
