# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

from datetime import datetime
from textwrap import dedent
from typing import Any

from weasyprint import HTML, CSS

from django.template import Template, Context

from Mark.services import MarkingTaskService
from Papers.services import SpecificationService
from . import DataExtractionService, MatplotlibService
from QuestionTags.services import QuestionTagService

report_html = """
    <body>
    <h2>Student report: {{longname}}</h2>
    {% if not all_marked %}
    <p style="color:red;">WARNING: Not all papers have been marked.</p>
    {% endif %}

    <p>Date: {{timestamp_str}}</p>
    <br>
    <h3>Overview</h3>
    <p>Name: {{name}}</p>
    <p>Student Number: {{sid}}</p>
    <p>Grade: {{grade}}/{{totalMarks}}</p>

    <br>
    <h3>Histogram of total marks</h3>
    <img src="data:image/png;base64,{{histogram_of_grades}}" />

    {% if pedagogy_tags_graph %}
    <br>
    <p style="break-before: page;"></p>
    <h3>Student achievement by topic or learning objective</h3>
    <img src="data:image/png;base64,{{pedagogy_tags_graph}}" />
    
    <p>
    Each question on this assessment was tagged by the instructor 
    with a topic or learning objective. Below is a lollypop graph 
    which indicates your mastery of the identified topic. The 
    score for each label is calculated as a weighted average of 
    the score on the associated questions.  
    </p>

    <p>
    For example, if Question 1 and Question 2 have the tag of 
    <q>Learning Objective 1</q>, with scores of 4/10 and 8/10 
    respectively, then the score for Learning Objective 1 is 
    calculated as the weighted average of the scores on 
    Questions 1 and 2: 1/2 (4/10+8/10) = 0.6.
    </p>
    <p>
    The labelling of questions is meant to help identify topics/areas 
    of strength and topics/areas for review.  If the score on a 
    topic is low, it is strongly recommended to review the associated 
    lecture notes, the associated section in the textbook, and/or 
    contact your instructor for an office hour.
    </p>
    {% endif %}

    <br>
    <p style="break-before: page;"></p>
    <h3>Histograms of marks by question</h3>
    {% for graph in histogram_of_grades_by_q %}
    <div class="col" style="margin-left:0mm;">
    <img src="data:image/png;base64,{{graph}}" width="100%" height="100%" />
    </div>
    {% endfor %}
   
"""


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
    df_filtered = df[df["StudentID"] == sid]
    # TODO: Probably should check there is only one row?

    student_dict = df_filtered.iloc[0].to_dict()
    name = student_dict["StudentName"]
    grade = int(student_dict["Total"])
    paper_number = int(student_dict["PaperNumber"])

    # histogram of grades
    if verbose:
        print("Histogram of total marks.")
    histogram_of_grades = mpls.histogram_of_total_marks(highlighted_sid=sid)
    pedagogy_tags_graph = None
    if sid is not None:
        if QuestionTagService.are_there_question_tag_links():
            # don't generate the lollypop graph is there are no pedagogy tags
            pedagogy_tags_graph = mpls.lollypop_of_pedagogy_tags(paper_number, sid)

    # histogram of grades for each question
    histogram_of_grades_by_q = []
    marks_for_questions = des._get_marks_for_all_questions()
    for _q, _ in enumerate(marks_for_questions):
        question_idx = _q + 1  # 1-indexing
        histogram_of_grades_by_q.append(  # add to the list
            # each base64-encoded image
            mpls.histogram_of_grades_on_question_version(
                question_idx, highlighted_sid=sid
            )
        )

    del marks_for_questions, question_idx, _  # clean up

    if verbose:
        print("\nGenerating HTML.")

    template= Template(report_html)
    context = Context(
        {
            "longname": longname,
            "timestamp_str": timestamp_str,
            "all_marked": all_marked,
            "name": name,
            "sid": sid,
            "grade": grade,
            "totalMarks": totalMarks,
            "histogram_of_grades": histogram_of_grades,
            "histogram_of_grades_by_q": histogram_of_grades_by_q,
            "pedagogy_tags_graph": pedagogy_tags_graph,
        }
    )
    rendered_html = template.render(context)
    pdf_data = HTML(string=rendered_html, base_url="").write_pdf(
        stylesheets=[CSS("./static/css/generate_report.css")]
    )
    filename = f"Student_Report-{shortname}--{name}--{sid}.pdf"
    return {
        "bytes": pdf_data,
        "filename": filename,
        "timestamp": timestamp,
    }
