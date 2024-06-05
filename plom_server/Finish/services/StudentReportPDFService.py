# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from datetime import datetime
from typing import Any, Dict, Optional
from textwrap import dedent

from tqdm import tqdm as _tqdm
from weasyprint import HTML, CSS

from Mark.services import MarkingTaskService
from Papers.services import SpecificationService
from . import DataExtractionService, MatplotlibService


def _identity_in_first_input(x, *args, **kwargs):
    return x


def pdf_builder(
    versions: bool,
    sid: Optional[str],
    *,
    verbose: Optional[bool] = None,
    _use_tqdm: bool = False,
) -> Dict[str, Any]:
    """Build a Student Report PDF file report and return it as bytes.

    Args:
        versions: Whether to include versions in the report.
        sid: student number.

    Keyword Args:
        verbose: print messages on the stdout.
        _use_tqdm: even more verbosity: use tqdm for progress bars.

    Returns:
        A dictionary with the bytes of a PDF file, a suggested
        filename, and the export timestamp.

    Raises:
        ValueError: lots of cases with NaN, usually indicating marking
            is incomplete, because the pandas library uses NaN for
            missing data.
    """
    tqdm: Any = _identity_in_first_input
    if _use_tqdm:
        tqdm = _tqdm

    if verbose:
        print("Building report.")
        print(
            dedent(
                """
                Graphs to generate:
                    1. Histogram of total marks (show student's standing)
                    2. Histogram of each question (show student's standing)
                    Generating."""
            )
        )

    des = DataExtractionService()
    mts = MarkingTaskService()
    mpls = MatplotlibService()

    # info for report
    shortname = SpecificationService.get_shortname()
    longname = SpecificationService.get_longname()
    totalMarks = SpecificationService.get_total_marks()
    timestamp = datetime.now()
    timestamp_str = timestamp.strftime("%d/%m/%Y %H:%M:%S+00:00")
    total_tasks = mts.get_n_total_tasks()
    all_marked = total_tasks > 0 and mts.get_n_marked_tasks() == total_tasks

    mpls.ensure_all_figures_closed()
    df = des.get_student_data()
    df_filtered = df[df["student_id"] == sid]
    # TODO: Probably should check there is only one row?

    student_dict = df_filtered.iloc[0].to_dict()
    name = student_dict["student_name"]
    grade = int(student_dict["total_mark"])

    # histogram of grades
    if verbose:
        print("Histogram of total marks.")
    histogram_of_grades = mpls.histogram_of_total_marks_highlighted(sid=sid)

    # histogram of grades for each question
    histogram_of_grades_q = []
    marks_for_questions = des._get_marks_for_all_questions()
    for _q, _ in tqdm(
        enumerate(marks_for_questions),
        desc="Histograms of marks by question",
    ):
        question_idx = _q + 1  # 1-indexing
        histogram_of_grades_q.append(  # add to the list
            # each base64-encoded image
            mpls.histogram_of_grades_on_question_highlighted(  # of the histogram
                question_idx, sid=sid
            )
        )

    del marks_for_questions, question_idx, _  # clean up

    if verbose:
        print("\nGenerating HTML.")

    def _html_add_title(title: str) -> str:
        """Generate HTML for a title."""
        out = f"""
        <br>
        <p style="break-before: page;"></p>
        <h3>{title}</h3>
        """
        return out

    def _html_for_graphs(list_of_graphs: list) -> str:
        """Generate HTML for a list of graphs."""
        out = ""
        odd = 0
        for i, graph in enumerate(list_of_graphs):
            odd = i % 2
            if not odd:
                out += """
                <div class="row">
                """
            out += f"""
            <div class="col" style="margin-left:0mm;">
            <img src="data:image/png;base64,{graph}" width="50px" height="40px" />
            </div>
            """
            if odd:
                out += """
                </div>
                """
        if not odd:
            out += """
            </div>
            """
        return out

    def _html_for_big_graphs(list_of_graphs: list) -> str:
        """Generate HTML for a list of large graphs."""
        out = ""
        for graph in list_of_graphs:
            out += f"""
            <div class="col" style="margin-left:0mm;">
            <img src="data:image/png;base64,{graph}" width="100%" height="100%" />
            </div>
            """
        return out

    html = f"""
    <body>
    <h2>Student report: {longname}</h2>
    """
    if not all_marked:
        html += """
        <p style="color:red;">WARNING: Not all papers have been marked.</p>
        """

    html += f"""
    <p>Date: {timestamp_str}</p>
    <br>
    <h3>Overview</h3>
    <p>Name: {name}</p>
    <p>Student Number: {sid}</p>
    <p>Grade: {grade}/{totalMarks}</p>
    <br>
    <h3>Histogram of total marks</h3>
    <img src="data:image/png;base64,{histogram_of_grades}" />
    """

    html += _html_add_title("Histogram of marks by question")
    html += _html_for_big_graphs(histogram_of_grades_q)

    pdf_data = HTML(string=html, base_url="").write_pdf(
        stylesheets=[CSS("./static/css/generate_report.css")]
    )
    filename = f"Student_Report-{shortname}--{name}--{sid}.pdf"
    return {
        "bytes": pdf_data,
        "filename": filename,
        "timestamp": timestamp,
    }
