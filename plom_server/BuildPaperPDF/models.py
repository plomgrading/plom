# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Aden Chan

from django.db import models
from pathlib import Path

# from django.db.models.signals import pre_delete

from plom_server.Base.models import HueyTaskTracker
from plom_server.Papers.models import Paper


class BuildPaperPDFChore(HueyTaskTracker):
    """Represents the chore of building a PDF file for each paper.

    paper (ForeignKey): a link to the associated paper being reassembled
    pdf_file (FileField): stores the reassembled pdf when it is built. Should not be directly exposed to users. Note that the name attribute associated with this field should not be exposed to users since it is simply the stub of the file which django has saved to disc and may contain superfluous characters for avoiding collisions.
    display_filename (TextField): stores the filename of the reassembled pdf to be returned to users.
    student_name (TextField): None or stores the student name used to pre-name the paper when built.
    student_id (TextField): None or stores the student id used to pre-name the paper when built.
    """

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
        # this should be called whenever the associated chore is obsolete.
        if self.pdf_file:
            Path(self.pdf_file.path).unlink(missing_ok=True)

    @classmethod
    def set_every_task_obsolete(cls, *, unlink_files: bool = False):
        super().set_every_task_obsolete()
        # set every single task to be obsolete
        for task in cls.objects.all():
            task.unlink_associated_pdf()
