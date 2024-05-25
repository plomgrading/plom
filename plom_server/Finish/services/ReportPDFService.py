# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from datetime import datetime
from typing import Any, Dict, Optional
from textwrap import dedent

from tqdm import tqdm as _tqdm
from weasyprint import HTML, CSS

from Mark.models import MarkingTask
from Mark.services import MarkingTaskService
from Papers.services import SpecificationService
from . import DataExtractionService, MatplotlibService 


def _identity_in_first_input(x, *args, **kwargs):
    return x


def pdf_builder(
    versions: bool, *, verbose: Optional[bool] = None, _use_tqdm: bool = False
) -> Dict[str, Any]:
    """Build a PDF file report and return it as bytes.

    Args:
        versions: Whether to include versions in the report.

    Keyword Args:
        verbose: print messages on the stdout
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
                    1. Histogram of total marks
                    2. Histogram of marks by question
                    3. Correlation heatmap
                    4. Histograms of grades by marker by question
                    5. Histograms of time spent marking each question
                    6. Scatter plots of time spent marking vs mark given
                    7. Box plots of grades given by marker by question
                    8. Line graph of average mark by question

                Generating..."""
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
    num_students = (
        MarkingTask.objects.values_list("paper__paper_number", flat=True)
        .distinct()
        .count()
    )
    average_mark = des.get_totals_average()
    median_mark = des.get_totals_median()
    stdev_mark = des.get_totals_stdev()
    total_tasks = mts.get_n_total_tasks()
    all_marked = mts.get_n_marked_tasks() == total_tasks and total_tasks > 0

    mpls.ensure_all_figures_closed()

    # histogram of grades
    if verbose:
        print("Histogram of total marks.")
    histogram_of_grades = mpls.histogram_of_total_marks()

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
            mpls.histogram_of_grades_on_question_version(  # of the histogram
                question_idx, versions=versions
            )
        )
    del marks_for_questions, question_idx, _  # clean up

    # correlation heatmap
    if verbose:
        print("Correlation heatmap.")
    corr = mpls.correlation_heatmap_of_questions()

    # histogram of grades given by each marker by question
    histogram_of_grades_m = []
    for marker, scores_for_user in tqdm(
        des._get_all_ta_data_by_ta().items(),
        desc="Histograms of marks by marker by question",
    ):
        questions_marked_by_this_ta = des.get_questions_marked_by_this_ta(
            marker,
        )
        histogram_of_grades_m_q = []

        for question_idx in questions_marked_by_this_ta:
            scores_for_user_for_question = des._get_ta_data_for_question(
                question_index=question_idx, ta_df=scores_for_user
            )

            histogram_of_grades_m_q.append(
                mpls.histogram_of_grades_on_question_by_ta(
                    question_idx,
                    ta_name=marker,
                    ta_df=scores_for_user_for_question,
                    versions=versions,
                )
            )

        histogram_of_grades_m.append(histogram_of_grades_m_q)

    # histogram of time taken to mark each question
    max_time = des._get_ta_data()["seconds_spent_marking"].max()
    bin_width = 15
    histogram_of_time = []
    for question, marking_times_df in tqdm(
        des._get_all_ta_data_by_question().items(),
        desc="Histograms of time spent marking each question",
    ):
        histogram_of_time.append(
            mpls.histogram_of_time_spent_marking_each_question(
                question,
                marking_times_df=marking_times_df,
                versions=versions,
                max_time=max_time,
                bin_width=bin_width,
            )
        )

    del max_time, bin_width

    # scatter plot of time taken to mark each question vs mark given
    scatter_of_time = []
    for question, marking_times_df in tqdm(
        des._get_all_ta_data_by_question().items(),
        desc="Scatter plots of time spent marking vs mark given",
    ):
        if versions:
            # list of lists of times spent marking each version of the question
            times_for_question = []
            marks_given_for_question = []
            for version in marking_times_df["question_version"].unique():
                version_df = marking_times_df[
                    (marking_times_df["question_version"] == version)
                ]
                times_for_question.append(
                    version_df["seconds_spent_marking"].div(60),
                )

                marks_given_for_question.append(version_df["score_given"])
        else:
            times_for_question = (
                marking_times_df["seconds_spent_marking"].div(60).to_list()
            )
            marks_given_for_question = des.get_scores_for_question(question)

        scatter_of_time.append(
            mpls.scatter_time_spent_vs_mark_given(
                question,
                times_spent_minutes=times_for_question,
                marks_given=marks_given_for_question,
                versions=versions,
            )
        )

    # Box plot of the grades given by each marker for each question
    boxplots = []
    for question_index, question_df in tqdm(
        des._get_all_ta_data_by_question().items(),
        desc="Box plots of marks given by marker by question",
    ):
        marks_given = []
        # add overall to names
        marker_names = ["Overall"]
        marker_names.extend(
            des.get_tas_that_marked_this_question(question_index, ta_df=question_df)
        )
        # add the overall marks
        marks_given.append(des.get_scores_for_question(question_index))

        for marker_name in marker_names[1:]:
            marks_given.append(
                des.get_scores_for_ta(ta_name=marker_name, ta_df=question_df),
            )

        boxplots.append(
            mpls.boxplot_of_marks_given_by_ta(marks_given, marker_names, question_index)
        )

    if verbose:
        print("Line graph of average mark by question.")
    line_graph = mpls.line_graph_of_avg_marks_by_question(versions=versions)

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
    <h2>Marking report: {longname}</h2>
    """
    if not all_marked:
        html += """
        <p style="color:red;">WARNING: Not all papers have been marked.</p>
        """

    html += f"""
    <p>Date: {timestamp_str}</p>
    <br>
    <h3>Overview</h3>
    <p>Number of students: {num_students}</p>
    <p>Average total mark: {average_mark:.2f}/{totalMarks}</p>
    <p>Median total mark: {median_mark}/{totalMarks}</p>
    <p>Standard deviation of total marks: {stdev_mark:.2f}</p>
    <br>
    <h3>Histogram of total marks</h3>
    <img src="data:image/png;base64,{histogram_of_grades}" />
    """

    html += _html_add_title("Histogram of marks by question")
    html += _html_for_big_graphs(histogram_of_grades_q)

    html += f"""
    <p style="break-before: page;"></p>
    <h3>Correlation heatmap</h3>
    <img src="data:image/png;base64,{corr}" />
    """

    html += _html_add_title("Histograms of grades by marker by question")

    for index, marker in enumerate(des._get_all_ta_data_by_ta()):
        html += f"""
        <h4>Grades by {marker}</h4>
        """
        html += _html_for_big_graphs(histogram_of_grades_m[index])

    html += _html_add_title(
        "Histograms of time spent marking each question (in minutes)"
    )
    html += _html_for_big_graphs(histogram_of_time)

    html += _html_add_title(
        "Scatter plots of time spent marking each question vs mark given"
    )
    html += _html_for_big_graphs(scatter_of_time)

    html += _html_add_title(
        "Box plots of grades given by each marker for each question"
    )
    html += _html_for_big_graphs(boxplots)

    html += _html_add_title("Line graph of average mark on each question")
    html += f"""
        <img src="data:image/png;base64,{line_graph}" />
        """

    pdf_data = HTML(string=html, base_url="").write_pdf(
        stylesheets=[CSS("./static/css/generate_report.css")]
    )
    timestamp_file = timestamp.strftime("%Y-%m-%d--%H-%M-%S+00-00")
    filename = f"Report-{shortname}--{timestamp_file}.pdf"
    return {
        "bytes": pdf_data,
        "filename": filename,
        "timestamp": timestamp,
    }
