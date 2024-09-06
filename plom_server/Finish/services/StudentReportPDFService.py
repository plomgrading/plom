# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

from datetime import datetime
from typing import Any

from weasyprint import HTML, CSS

from django.template.loader import get_template

from Mark.services import MarkingTaskService
from Papers.services import SpecificationService
from . import DataExtractionService, MatplotlibService
from QuestionTags.services import QuestionTagService

from plom.misc_utils import pprint_score


def pdf_builder(
    versions: bool,
    sid: str | None,
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Build a Student Report PDF file report and return it as bytes.

    Args:
        versions: Whether to include versions in the report.
        sid: student number.

    Keyword Args:
        verbose: print messages on the stdout.

    Returns:
        A dictionary with the bytes of a PDF file, a suggested
        filename, and the export timestamp.

    Raises:
        ValueError: lots of cases with NaN, usually indicating marking
            is incomplete, because the pandas library uses NaN for
            missing data.
    """
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
    df_filtered = df[df["StudentID"] == sid]
    # TODO: Probably should check there is only one row?

    student_dict = df_filtered.iloc[0].to_dict()
    name = student_dict["StudentName"]
    grade = pprint_score(student_dict["Total"])
    paper_number = int(student_dict["PaperNumber"])
    total_stats = des.get_descriptive_statistics_of_total()

    kde_of_total_marks = mpls.kde_plot_of_total_marks(highlighted_sid=sid)
    pedagogy_tags_graph = None
    pedagogy_tags_descriptions = QuestionTagService.get_pedagogy_tag_descriptions()
    if sid is not None:
        if QuestionTagService.are_there_question_tag_links():
            # don't generate the lollypop graph is there are no pedagogy tags
            pedagogy_tags_graph = mpls.lollypop_of_pedagogy_tags(paper_number, sid)

    # boxplot of marks for each question
    boxplot_of_question_marks = []
    marks_for_questions = des._get_marks_for_all_questions()
    for _q, _ in enumerate(marks_for_questions):
        question_idx = _q + 1  # 1-indexing
        boxplot_of_question_marks.append(  # add to the list
            # each base64-encoded image
            mpls.boxplot_of_grades_on_question_version(
                question_idx, highlighted_sid=sid
            )
        )

    del marks_for_questions, question_idx, _  # clean up

    report_template = get_template("Finish/Reports/report_for_students.html")
    context = {
        "longname": longname,
        "timestamp_str": timestamp_str,
        "all_marked": all_marked,
        "name": name,
        "sid": sid,
        "grade": grade,
        "totalMarks": totalMarks,
        "total_stats": total_stats,
        "pedagogy_tags_graph": pedagogy_tags_graph,
        "pedagogy_tags_descriptions": pedagogy_tags_descriptions,
        "boxplots": boxplot_of_question_marks,
        "kde_graph": kde_of_total_marks,
    }

    rendered_html = report_template.render(context)
    pdf_data = HTML(string=rendered_html, base_url="").write_pdf(
        stylesheets=[CSS("./static/css/generate_report.css")]
    )
    filename = f"Student_Report-{shortname}--{name}--{sid}.pdf"
    return {
        "bytes": pdf_data,
        "filename": filename,
        "timestamp": timestamp,
    }
