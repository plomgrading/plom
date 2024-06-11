# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from django.db import models

from Base.models import HueyTaskTracker
from Papers.models import Paper


class ReassemblePaperChore(HueyTaskTracker):
    """A tracker for the huey chore of reassembling marked papers

    paper (ForeignKey): a link to the associated paper being reassembled
    pdf_file (FileField): stores the reassembled pdf when it is built. Should not be directly exposed to users. Note that the name attribute associated with this field should not be exposed to users since it is simply the stub of the file which django has saved to disc and may contain superfluous characters for avoiding collisions.
    display_filename (TextField): stores the filename of the reassembled pdf to be returned to users.
    """

    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)
    pdf_file = models.FileField(upload_to="reassembled/", null=True)
    display_filename = models.TextField(null=True)

    def __str__(self):
        """Stringify task using its related test-paper's number."""
        return "Reassemble Paper Chore " + str(self.paper.paper_number)


class BuildSolutionPDFChore(HueyTaskTracker):
    """A tracker for the huey chore of building solution pdfs for papers

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
    version = models.PositiveIntegerField(null=False)
    solution_number = models.PositiveIntegerField(null=False)
    image = models.ImageField(upload_to="sourceVersions")
