# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.db import models

from Base.models import HueyTask
from Papers.models import Paper


class PDFTask(HueyTask):
    paper = models.OneToOneField(Paper, null=False, on_delete=models.CASCADE)
    pdf_file_path = models.TextField(default="")
    student_name = models.TextField(default=None, null=True)
    student_id = models.TextField(default=None, null=True)

    def __str__(self):
        return "Task Object " + str(self.paper_number)
