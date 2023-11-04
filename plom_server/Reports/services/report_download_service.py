# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import datetime as dt

from weasyprint import HTML, CSS

from Finish.services import DataExtractionService, MatplotlibService
from Mark.models import MarkingTask
from Mark.services import MarkingTaskService
from Papers.services import SpecificationService


class ReportDownloadService:
    """Class to encapsulate code for downloading the report."""

    def get_report_bytes(self, versions: bool) -> str:
        """Get the report as a string.

        Args:
            versions: Whether to include versions in the report.

        Returns:
            The report as a bytes object.
        """
        des = DataExtractionService()
        mts = MarkingTaskService()
        mpls = MatplotlibService()

        # info for report
        longName = SpecificationService.get_longname()
        totalMarks = SpecificationService.get_total_marks()
        date = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S+00:00")
        num_students = (
            MarkingTask.objects.values_list("paper__paper_number", flat=True)
            .distinct()
            .count()
        )
        average_mark = des.get_total_average_mark()
        median_mark = des.get_total_median_mark()
        stdev_mark = des.get_total_stdev_mark()
        total_tasks = mts.get_n_total_tasks()
        all_marked = mts.get_n_marked_tasks() == total_tasks and total_tasks > 0

        mpls.ensure_all_figures_closed()

        # histogram of grades
        histogram_of_grades = mpls.histogram_of_total_marks()

        # histogram of grades for each question
        histogram_of_grades_q = []
        marks_for_questions = des._get_marks_for_all_questions()
        for question, _ in enumerate(marks_for_questions):
            question += 1  # 1-indexing
            histogram_of_grades_q.append(  # add to the list
                # each base64-encoded image
                mpls.histogram_of_grades_on_question_version(  # of the histogram
                    question=question, versions=versions
                )
            )

        del marks_for_questions, question, _  # clean up

        # correlation heatmap
        corr = mpls.correlation_heatmap_of_questions()

        # histogram of grades given by each marker by question
        histogram_of_grades_m = []
        for marker, scores_for_user in des._get_all_ta_data_by_ta().items():
            questions_marked_by_this_ta = des.get_questions_marked_by_this_ta(
                marker,
            )
            histogram_of_grades_m_q = []

            for question in questions_marked_by_this_ta:
                scores_for_user_for_question = des._get_ta_data_for_question(
                    question_number=question, ta_df=scores_for_user
                )

                histogram_of_grades_m_q.append(
                    mpls.histogram_of_grades_on_question_by_ta(
                        question=question,
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
        for question, marking_times_df in des._get_all_ta_data_by_question().items():
            histogram_of_time.append(
                mpls.histogram_of_time_spent_marking_each_question(
                    question_number=question,
                    marking_times_df=marking_times_df,
                    versions=versions,
                    max_time=max_time,
                    bin_width=bin_width,
                )
            )

        del max_time, bin_width

        # scatter plot of time taken to mark each question vs mark given
        scatter_of_time = []
        for question, marking_times_df in des._get_all_ta_data_by_question().items():
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
                marks_given_for_question = des.get_scores_for_question(
                    question_number=question,
                )

            scatter_of_time.append(
                mpls.scatter_time_spent_vs_mark_given(
                    question_number=question,
                    times_spent_minutes=times_for_question,
                    marks_given=marks_given_for_question,
                    versions=versions,
                )
            )

        # Box plot of the grades given by each marker for each question
        boxplots = []
        for question_number, question_df in des._get_all_ta_data_by_question().items():
            marks_given = []
            # add overall to names
            marker_names = ["Overall"]
            marker_names.extend(
                des.get_tas_that_marked_this_question(
                    question_number, ta_df=question_df
                )
            )
            # add the overall marks
            marks_given.append(
                des.get_scores_for_question(
                    question_number=question_number,
                )
            )

            for marker_name in marker_names[1:]:
                marks_given.append(
                    des.get_scores_for_ta(ta_name=marker_name, ta_df=question_df),
                )

            boxplots.append(
                mpls.boxplot_of_marks_given_by_ta(
                    marks_given, marker_names, question_number
                )
            )

        # line graph of average mark on each question
        line_graph = mpls.line_graph_of_avg_marks_by_question(versions=versions)

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
                    out += f"""
                    <div class="row">
                    """
                out += f"""
                <div class="col" style="margin-left:0mm;">
                <img src="data:image/png;base64,{graph}" width="50px" height="40px">
                </div>
                """
                if odd:
                    out += f"""
                    </div>
                    """
            if not odd:
                out += f"""
                </div>
                """
            return out

        def _html_for_big_graphs(list_of_graphs: list) -> str:
            """Generate HTML for a list of large graphs."""
            out = ""
            for graph in list_of_graphs:
                out += f"""
                <div class="col" style="margin-left:0mm;">
                <img src="data:image/png;base64,{graph}" width="100%" height="100%">
                </div>
                """
            return out

        html = f"""
        <body>
        <h2>Marking report: {longName}</h2>
        """
        if not all_marked:
            html += f"""
            <p style="color:red;">WARNING: Not all papers have been marked.</p>
            """

        html += f"""
        <p>Date: {date}</p>
        <br>
        <h3>Overview</h3>
        <p>Number of students: {num_students}</p>
        <p>Average total mark: {average_mark:.2f}/{totalMarks}</p>
        <p>Median total mark: {median_mark}/{totalMarks}</p>
        <p>Standard deviation of total marks: {stdev_mark:.2f}</p>
        <br>
        <h3>Histogram of total marks</h3>
        <img src="data:image/png;base64,{histogram_of_grades}">
        """

        html += _html_add_title("Histogram of marks by question")
        html += _html_for_big_graphs(histogram_of_grades_q)

        html += f"""
        <p style="break-before: page;"></p>
        <h3>Correlation heatmap</h3>
        <img src="data:image/png;base64,{corr}">
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
            <img src="data:image/png;base64,{line_graph}">
            """

        return HTML(string=html, base_url="").write_pdf(
            stylesheets=[CSS("./static/css/generate_report.css")]
        )
