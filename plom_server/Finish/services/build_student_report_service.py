# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024-2025 Andrew Rechnitzer

from datetime import datetime
from pathlib import Path
from statistics import mean, median, mode, stdev, quantiles
from typing import Any

from Papers.models import Paper
from Papers.services import SpecificationService
from ..services import StudentMarkService
from .StudentReportPDFService import pdf_builder


def _get_descriptive_statistics_from_score_list(
    scores: list[float],
) -> dict[str, float]:
    """Return descriptive statistics from a list of scores

    Gives dict of count, max, min, median, mean, mode, stddev, percentile25, percentile75.
    """
    quants = quantiles(scores)
    return {
        "count": len(scores),
        "max": max(scores),
        "min": min(scores),
        "median": median(scores),
        "mean": mean(scores),
        "mode": mode(scores),
        "stddev": stdev(scores),
        "percentile25": quants[0],
        "percentile75": quants[1],
    }


def brief_report_pdf_builder(
    paper_number,
    total_score_list: list[float],
    question_score_lists: dict[int, list[float]],
) -> dict[str, Any]:
    """Build a Student Report PDF file report and return it as bytes.

    Args:
        paper_number: the number of the paper

    Returns:
        A dictionary with the bytes of a PDF file, a suggested
        filename, and the export timestamp.

    Raises:
        ValueError: lots of cases with NaN, usually indicating marking
            is incomplete, because the pandas library uses NaN for
            missing data.
    """
    from django.template.loader import get_template
    from weasyprint import HTML, CSS

    paper_info = StudentMarkService.get_paper_id_and_marks(paper_number)
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%d/%m/%Y %H:%M:%S+00:00")
    context = {
        "longname": SpecificationService.get_longname(),
        "timestamp_str": timestamp_str,
        "totalMarks": SpecificationService.get_total_marks(),
        "name": paper_info["name"],
        "sid": paper_info["sid"],
        "grade": paper_info["total"],
        "total_stats": _get_descriptive_statistics_from_score_list(total_score_list),
    }
    report_template = get_template("Finish/Reports/brief_student_report.html")
    rendered_html = report_template.render(context)
    pdf_data = HTML(string=rendered_html, base_url="").write_pdf(
        stylesheets=[CSS("./static/css/generate_report.css")]
    )
    shortname = (SpecificationService.get_shortname(),)
    sname = paper_info["name"]
    sid = paper_info["sid"]
    filename = f"Student_Report-{shortname}--{sname}--{sid}.pdf"
    return {
        "bytes": pdf_data,
        "filename": filename,
        "timestamp": timestamp,
    }


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

    def build_brief_report(
        self,
        paper_number: int,
        total_score_list: list[float],
        question_score_lists: dict[int, list[float]],
    ) -> dict[str, Any]:

        outdir = Path("student_report")
        outdir.mkdir(exist_ok=True)

        return brief_report_pdf_builder(
            paper_number, total_score_list, question_score_lists
        )
