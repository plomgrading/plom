# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2025 Andrew Rechnitzer

from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any

from tqdm import tqdm as _tqdm
from weasyprint import HTML, CSS

from plom_server.Mark.models import MarkingTask
from plom_server.Mark.services import MarkingTaskService
from plom_server.Papers.services import SpecificationService
from . import DataExtractionService, MatplotlibService


def _identity_in_first_input(x, *args, **kwargs):
    return x


GRAPH_DETAILS = {
    "graph1": {"title": "Histogram of total marks", "default": True},
    "graph2": {"title": "Histogram of marks by question", "default": False},
    "graph3": {"title": "Correlation heatmap", "default": False},
    "graph4": {"title": "Histograms of marks by marker by question", "default": False},
    "graph5": {
        "title": "Histograms of time spent marking each question",
        "default": False,
    },
    "graph6": {
        "title": "Scatter plots of time spent marking vs mark given",
        "default": False,
    },
    "graph7": {
        "title": "Box plots of question marks by TA who marked",
        "default": False,
    },
    "graph8": {"title": "Line graph of average mark by question", "default": False},
}


def pdf_builder(
    versions: bool,
    *,
    verbose: bool = False,
    _use_tqdm: bool = False,
    brief: bool = False,
    selected_graphs: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Build a PDF file report and return it as bytes.

    Args:
        versions: Whether to include versions in the report.
        brief: Whether to generate a brief report.
        selected_graphs: Selected graphs for the brief report.

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
                    4. Histograms of marks by marker by question
                    5. Histograms of time spent marking each question
                    6. Scatter plots of time spent marking vs mark given
                    7. Box plots of marks given by marker by question
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

    # Initialize the graphs dictionary
    graphs: dict[str, list[Any]] = {key: [] for key in GRAPH_DETAILS}
    selected_graphs = selected_graphs or {}

    if verbose:
        print("Histogram of total marks.")
    graphs["graph1"].append(mpls.histogram_of_total_marks())

    if not brief or selected_graphs.get("graph2"):
        marks_for_questions = des._get_marks_for_all_questions()
        graphs["graph2"] = [
            mpls.histogram_of_grades_on_question_version(_q + 1, versions=versions)
            for _q, _ in tqdm(
                enumerate(marks_for_questions),
                desc="Histograms of marks by question",
            )
        ]

    if not brief or selected_graphs.get("graph3"):
        if verbose:
            print("Correlation heatmap.")
        graphs["graph3"].append(mpls.correlation_heatmap_of_questions())

    if not brief or selected_graphs.get("graph4"):
        for marker, scores_for_user in tqdm(
            des._get_all_ta_data_by_ta().items(),
            desc="Histograms of marks by marker by question",
        ):
            questions_marked_by_this_ta = des.get_questions_marked_by_this_ta(marker)
            graphs["graph4"].append(
                [
                    mpls.histogram_of_grades_on_question_by_ta(
                        question_idx,
                        ta_name=marker,
                        ta_df=des._get_ta_data_for_question(
                            question_idx, ta_df=scores_for_user
                        ),
                        versions=versions,
                    )
                    for question_idx in questions_marked_by_this_ta
                ]
            )

    if not brief or selected_graphs.get("graph5"):
        max_time = des._get_ta_data()["seconds_spent_marking"].max()
        bin_width = 15
        graphs["graph5"] = [
            mpls.histogram_of_time_spent_marking_each_question(
                qidx,
                marking_times_df=marking_times_df,
                versions=versions,
                max_time=max_time,
                bin_width=bin_width,
            )
            for qidx, marking_times_df in tqdm(
                des._get_all_ta_data_by_qidx().items(),
                desc="Histograms of time spent marking each question",
            )
        ]

    if not brief or selected_graphs.get("graph6"):
        # Note: the marking_times_df seems to be used only to get the list
        # of versions involved in each question: the "des" helper functions
        # are re-filtering by qidx.
        graphs["graph6"] = [
            mpls.scatter_time_spent_vs_mark_given(
                qidx,
                times_spent_minutes=(
                    [des._get_marking_times_for_qidx(qidx)]
                    if not versions
                    else [
                        des._get_marking_times_for_qidx(qidx, ver=v)
                        for v in sorted(marking_times_df["question_version"].unique())
                    ]
                ),
                marks_given=(
                    [des._get_scores_for_qidx(qidx)]
                    if not versions
                    else [
                        des._get_scores_for_qidx(qidx, ver=v)
                        for v in sorted(marking_times_df["question_version"].unique())
                    ]
                ),
                versions=versions,
            )
            for qidx, marking_times_df in tqdm(
                des._get_all_ta_data_by_qidx().items(),
                desc="Scatter plots of time spent marking vs mark given",
            )
        ]

    if not brief or selected_graphs.get("graph7"):
        graphs["graph7"] = [
            mpls.boxplot_of_marks_given_by_ta(
                [des._get_scores_for_qidx(qidx)]
                + [
                    des.get_scores_for_ta(ta_name=marker_name, ta_df=question_df)
                    for marker_name in des.get_tas_that_marked_this_question(
                        qidx, ta_df=question_df
                    )
                ],
                ["Overall"]
                + des.get_tas_that_marked_this_question(qidx, ta_df=question_df),
                qidx,
            )
            for qidx, question_df in tqdm(
                des._get_all_ta_data_by_qidx().items(),
                desc="Box plots of marks given by marker by question",
            )
        ]

    if not brief or selected_graphs.get("graph8"):
        graphs["graph8"].append(
            mpls.line_graph_of_avg_marks_by_question(versions=versions)
        )

    if verbose:
        print("\nGenerating HTML.")

    def _html_add_title(title: str) -> str:
        """Generate HTML for a title."""
        return f"""
        <br>
        <p style="break-before: page;"></p>
        <h3>{str(title)}</h3>
        """

    def _html_for_graphs(list_of_graphs: list[Any]) -> str:
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

    def _html_for_big_graphs(list_of_graphs: list[Any]) -> str:
        """Generate HTML for a list of large graphs."""
        return "".join(
            [
                f"""
            <div class="col" style="margin-left:0mm;">
            <img src="data:image/png;base64,{graph}" width="100%" height="100%" />
            </div>
            """
                for graph in list_of_graphs
            ]
        )

    html = f"""
    <body>
    <h2>{'Brief Report' if brief else 'Marking report'}: {longname if not brief else ''}</h2>
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
    <img src="data:image/png;base64,{graphs["graph1"][0]}" />
    """

    if not brief:
        html += _html_add_title(str(GRAPH_DETAILS["graph2"]["title"]))
        html += _html_for_big_graphs(graphs["graph2"])

        html += f"""
        <p style="break-before: page;"></p>
        <h3>{GRAPH_DETAILS["graph3"]["title"]}</h3>
        <img src="data:image/png;base64,{graphs["graph3"][0]}" />
        """

        html += _html_add_title(str(GRAPH_DETAILS["graph4"]["title"]))

        for index, marker in enumerate(des._get_all_ta_data_by_ta()):
            html += f"""
            <h4>Marks by {marker}</h4>
            """
            html += _html_for_big_graphs(graphs["graph4"][index])

        html += _html_add_title(str(GRAPH_DETAILS["graph5"]["title"]))
        html += _html_for_big_graphs(graphs["graph5"])

        html += _html_add_title(str(GRAPH_DETAILS["graph6"]["title"]))
        html += _html_for_big_graphs(graphs["graph6"])

        html += _html_add_title(str(GRAPH_DETAILS["graph7"]["title"]))
        html += _html_for_big_graphs(graphs["graph7"])

        html += _html_add_title(str(GRAPH_DETAILS["graph8"]["title"]))
        html += f"""
            <img src="data:image/png;base64,{graphs["graph8"][0]}" />
            """
    else:
        if selected_graphs.get("graph2"):
            html += _html_add_title(str(GRAPH_DETAILS["graph2"]["title"]))
            html += _html_for_big_graphs(graphs["graph2"])

        if selected_graphs.get("graph3"):
            html += f"""
            <p style="break-before: page;"></p>
            <h3>{GRAPH_DETAILS["graph3"]["title"]}</h3>
            <img src="data:image/png;base64,{graphs["graph3"][0]}" />
            """

        if selected_graphs.get("graph4"):
            html += _html_add_title(str(GRAPH_DETAILS["graph4"]["title"]))

            for index, marker in enumerate(des._get_all_ta_data_by_ta()):
                html += f"""
                <h4>Marks by {marker}</h4>
                """
                html += _html_for_big_graphs(graphs["graph4"][index])

        if selected_graphs.get("graph5"):
            html += _html_add_title(str(GRAPH_DETAILS["graph5"]["title"]))
            html += _html_for_big_graphs(graphs["graph5"])

        if selected_graphs.get("graph6"):
            html += _html_add_title(str(GRAPH_DETAILS["graph6"]["title"]))
            html += _html_for_big_graphs(graphs["graph6"])

        if selected_graphs.get("graph7"):
            html += _html_add_title(str(GRAPH_DETAILS["graph7"]["title"]))
            html += _html_for_big_graphs(graphs["graph7"])

        if selected_graphs.get("graph8"):
            html += _html_add_title(str(GRAPH_DETAILS["graph8"]["title"]))
            html += f"""
                <img src="data:image/png;base64,{graphs["graph8"][0]}" />
                """

    # We want this, but done "properly":
    # # css = CSS("./static/css/generate_report.css")
    # see also discussion in build_student_report_service.py
    import plom_server

    path = Path(plom_server.__path__[0]) / "static/css/generate_report.css"
    css = CSS(path)

    pdf_data = HTML(string=html, base_url="").write_pdf(stylesheets=[css])
    timestamp_file = timestamp.strftime("%Y-%m-%d--%H-%M-%S+00-00")
    filename = f"Report-{shortname}--{timestamp_file}.pdf"
    return {
        "bytes": pdf_data,
        "filename": filename,
        "timestamp": timestamp,
    }
