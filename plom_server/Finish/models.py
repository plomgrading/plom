# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023, 2025 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady

from django.db import models

from plom_server.Base.models import HueyTaskTracker
from plom_server.Papers.models import Paper


class ReassemblePaperChore(HueyTaskTracker):
    """A tracker for the huey chore of reassembling marked papers.

    paper (ForeignKey): a link to the associated paper being reassembled
    pdf_file (FileField): stores the reassembled pdf when it is built. Should not be directly exposed to users. Note that the name attribute associated with this field should not be exposed to users since it is simply the stub of the file which django has saved to disc and may contain superfluous characters for avoiding collisions.
    display_filename (TextField): stores the filename of the reassembled pdf to be returned to users.
    report_pdf_file (FileField): stores the student_report pdf when it is built. Should not be directly exposed to users.
    report_display_filename (TextField): stores the filename of the report pdf to be returned to users.
    """

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    pdf_file = models.FileField(upload_to="reassembled/", null=True)
    display_filename = models.TextField(null=True)
    report_pdf_file = models.FileField(upload_to="student_report/", null=True)
    report_display_filename = models.TextField(null=True)

    def __str__(self):
        """Stringify task using its related test-paper's number."""
        return "Reassemble Paper Chore " + str(self.paper.paper_number)


class BuildSolutionPDFChore(HueyTaskTracker):
    """A tracker for the huey chore of building solution pdfs for papers.

    paper (ForeignKey): a link to the paper for which we are making the solution pdf.
    pdf_file (FileField): stores the solution pdf when it is built. Should not be directly exposed to users. Note that the name attribute associated with this field should not be exposed to users since it is simply the stub of the file which django has saved to disc and may contain superfluous characters for avoiding collisions.
    display_filename (TextField): stores the filename of the solution pdf to be returned to users.
    """

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)

    pdf_file = models.FileField(upload_to="solutions/", null=True)
    display_filename = models.TextField(null=True)

    def __str__(self):
        """Stringify task using its related test-paper's number."""
        return "Build Solution PDF Chore " + str(self.paper.paper_number)


class SolutionSourcePDF(models.Model):
    version = models.PositiveIntegerField(unique=True)
    source_pdf = models.FileField(upload_to="sourceVersions")
    pdf_hash = models.CharField(null=False, max_length=64)


class SolutionImage(models.Model):
    """An image of the solution to a version of a question.

    A cached copy of the rendered PDF file.

    question_index: which question.
    version: which version.
    image: an abstraction of a file for the image.
    height: how many pixels high is the image.
    width: how many pixels wide is the image.
    """

    question_index = models.PositiveIntegerField(null=False)
    version = models.PositiveIntegerField(null=False)
    image_file = models.ImageField(
        null=False,
        upload_to="sourceVersions",
        # tell Django where to automagically store height/width info on save
        height_field="height",
        width_field="width",
    )
    height = models.IntegerField(default=0)
    width = models.IntegerField(default=0)
