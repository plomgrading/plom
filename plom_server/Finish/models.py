# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from django.db import models

from Base.models import HueyTaskTracker
from Papers.models import Paper


class ReassemblePaperChore(HueyTaskTracker):
    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)

    pdf_file = models.FileField(upload_to="reassemble/", null=True)

    def __str__(self):
        """Stringify task using its related test-paper's number."""
        return "Reassemble Paper Chore " + str(self.paper.paper_number)


class BuildSolutionPDFChore(HueyTaskTracker):
    paper = models.ForeignKey(Paper, null=False, on_delete=models.CASCADE)

    pdf_file = models.FileField(upload_to="solutions/", null=True)

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
