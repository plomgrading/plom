# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady

from .StudentReportPDFService import pdf_builder
from ..services import StudentMarkService
from Papers.services import SpecificationService
from ..models import Paper
from pathlib import Path
from typing import List


class BuildStudentReportService:
    """Class that contains helper functions for building student report pdf."""

    def build_one_report(self, paper_number: int):
        """Build student report for the given paper number.

        Args:
        paper_number: the paper_number to be built a report.

        Returns:
        Student Report as PDF file in bytes
        """
        paper = Paper.objects.get(paper_number=paper_number)

        sms = StudentMarkService()
        paper_info = sms.get_paper_id_or_none(paper)
        if paper_info:
            sid, sname = paper_info
        else:
            sid, sname = None, None

        outdir = Path("student_report")
        outdir.mkdir(exist_ok=True)

        report = pdf_builder(versions=True, sid=sid)
        return report

    def get_status_for_student_report(self) -> List[int]:
        """Retrieve status, such as number of scanned, marked, identified and ready to build papers.

        Return:
        A list comprising number of scanned, marked, identified,
        and built-ready papers respectively.
        """
        sms = StudentMarkService()

        total_questions = SpecificationService.get_n_questions()
        num_scanned = 0
        num_fully_marked = 0
        num_identified = 0
        num_ready = 0

        for paper in Paper.objects.all():
            scanned, identified, num_marked, last_updated = sms.get_paper_status(paper)
            if scanned:
                num_scanned += 1
            if identified:
                num_identified += 1
            if num_marked == total_questions:
                num_fully_marked += 1
                if identified:
                    num_ready += 1

        return [num_scanned, num_fully_marked, num_identified, num_ready]
