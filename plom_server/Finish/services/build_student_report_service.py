# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from pathlib import Path
from typing import Any

from Papers.models import Paper
from ..services import StudentMarkService
from .StudentReportPDFService import pdf_builder


class BuildStudentReportService:
    """Class that contains helper functions for building student report pdf."""

    def build_one_report(self, paper_number: int) -> dict[str, Any]:
        """Build student report for the given paper number.

        Args:
            paper_number: the paper_number to be built a report.

        Returns:
            A dictionary with student report PDF file in bytes.
        """
        paper = Paper.objects.get(paper_number=paper_number)

        paper_info = StudentMarkService.get_paper_id_or_none(paper)
        if paper_info:
            sid = paper_info[0]
        else:
            sid = None

        outdir = Path("student_report")
        outdir.mkdir(exist_ok=True)

        report = pdf_builder(versions=True, sid=sid)
        return report
