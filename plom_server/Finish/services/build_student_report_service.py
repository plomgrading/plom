# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady

from .StudentReportPDFService import pdf_builder
from ..services import StudentMarkService
from ..models import Paper
from pathlib import Path


class BuildStudentReportService:
    """Class that contains helper functions for building student report pdf"""

    def build_one_report(paper_number: int):
        """Build student report for the given paper number

        Args:
        paper_number: the paper_number to be built a report

        Return:
        Student Report as PDF file in bytes"""
        paper = Paper.objects.get(paper_number=paper_number)

        sms = StudentMarkService()
        paper_info = sms.get_paper_id_or_none(paper)
        sid, sname = paper_info

        outdir = Path("student_report")
        outdir = Path(outdir)
        outdir.mkdir(exist_ok=True)
        print("DEBUG: ", outdir)

        report = pdf_builder(versions=True, sid=sid)
        return report
