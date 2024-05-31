# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady

from .StudentReportPDFService import pdf_builder
from ..services import StudentMarkService
from ..models import Paper
from pathlib import Path


class BuildStudentReportService:
    """Class that contains helper functions for building student report pdf"""

    def build_one_report(paper_number: int):
        """Build student report for the given paper number"""
        paper = Paper.objects.get(paper_number=paper_number)

        sms = StudentMarkService()
        sid, sname = sms.get_paper_id_or_none(paper)

        outdir = Path("student_report")
        outdir = Path(outdir)
        outdir.mkdir(exist_ok=True)

        report = pdf_builder(versions=True, sid=sid)
        return report
