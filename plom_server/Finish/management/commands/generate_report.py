# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import base64
import datetime as dt
from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from weasyprint import HTML, CSS

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from Finish.services import StudentMarkService, TaMarkingService, GraphingDataService
from Mark.models import MarkingTask
from Mark.services import MarkingTaskService
from Papers.models import Specification

RANGE_BIN_OFFSET = 2


class Command(BaseCommand):
    """Generates a PDF report of the marking progress."""

    help = """Generates a PDF report of the marking progress.

    Requires matplotlib, pandas, seaborn, and weasyprint. If calling on demo
    data, run `python manage.py plom_demo --randomarker` first.
    """

    matplotlib.use("Pdf")

    def handle(self, *args, **options):
        print("Building report.")

        gds = GraphingDataService()
        sms = StudentMarkService()
        tms = TaMarkingService()
        mts = MarkingTaskService()
        spec = Specification.load().spec_dict

        student_df = sms.get_all_students_download(
            version_info=True, timing_info=True, warning_info=False
        )
        student_keys = sms.get_csv_header(
            spec, version_info=True, timing_info=True, warning_info=False
        )
        marks = pd.DataFrame(student_df, columns=student_keys)

        ta_df = tms.build_csv_data()
        ta_keys = tms.get_csv_header()

        ta_grading = pd.DataFrame(ta_df, columns=ta_keys)
        ta_times = ta_grading.copy(deep=True)

        # info for report
        name = spec["name"]
        longName = spec["longName"]
        totalMarks = spec["totalMarks"]
        date = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S+00:00")
        num_students = (
            MarkingTask.objects.values_list("paper__paper_number", flat=True)
            .distinct()
            .count()
        )
        average_mark = gds.get_total_average_mark()
        median_mark = gds.get_total_median_mark()
        stdev_mark = gds.get_total_stdev_mark()
        total_tasks = mts.get_n_total_tasks()
        all_marked = mts.get_n_marked_tasks() == total_tasks and total_tasks > 0

        def debug_print_var(var):
            """DEBUG: Print the variable and its type."""
            print(var)
            print("type: ", type(var))

        def check_num_figs():
            if len(plt.get_fignums()) > 0:
                print("Warn: ", len(plt.get_fignums()), " figures open.")

        check_num_figs()

        # histogram of grades
        print("Generating histogram of grades.")
        fig, ax = plt.subplots()

        ax.hist(
            gds.get_total_marks(),
            bins=range(0, totalMarks + RANGE_BIN_OFFSET),
            ec="black",
            alpha=0.5,
        )
        ax.set_title("Histogram of total marks")
        ax.set_xlabel("Total mark")
        ax.set_ylabel("# of students")

        base64_histogram_of_grades = gds.get_graph_as_base64(fig)

        check_num_figs()

        # histogram of grades for each question
        print("Generating histograms of grades by question.")
        base64_histogram_of_grades_q = []
        marks_for_questions = gds.get_marks_for_all_questions()
        for i, marks_for_question in enumerate(marks_for_questions):
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

            bins = range(0, spec["question"][str(i + 1)]["mark"] + RANGE_BIN_OFFSET)

            ax.hist(marks_for_question, bins=bins, ec="black", alpha=0.5)
            ax.set_title("Histogram of Q" + str(i + 1) + " marks")
            ax.set_xlabel("Question " + str(i + 1) + " mark")
            ax.set_ylabel("# of students")

            base64_histogram_of_grades_q.append(gds.get_graph_as_base64(fig))

            check_num_figs()

        # correlation heatmap
        print("Generating correlation heatmap.")
        marks_corr = gds.get_question_correlation_heatmap()

        plt.figure(figsize=(6.4, 5.12))
        sns.heatmap(
            marks_corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, square=True
        )
        plt.title("Correlation between questions")
        plt.xlabel("Question number")
        plt.ylabel("Question number")

        base64_corr = gds.get_graph_as_base64(plt.gcf())

        if len(plt.get_fignums()) > 0:
            print("Warn: ", len(plt.get_fignums()), " figures open.")

        # histogram of grades given by each marker by question
        print("Generating histograms of grades given by marker by question.")
        marks_by_tas = gds.get_marks_for_all_tas()
        base64_histogram_of_grades_m = []

        for marker in marks_by_tas:
            scores_for_user = marks_by_tas[marker]
            base64_histogram_of_grades_m_q = []

            for question in scores_for_user["question_number"].unique():
                scores_for_user_for_question = scores_for_user.loc[
                    scores_for_user["question_number"] == question
                ]  # TODO: factor this out into graphing_data_service.py

                fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)
                bins = range(
                    0,
                    scores_for_user_for_question["max_score"].max() + RANGE_BIN_OFFSET,
                )

                ax.hist(
                    scores_for_user_for_question["score_given"],
                    bins=bins,
                    ec="black",
                    alpha=0.5,
                )
                ax.set_title("Grades for Q" + str(question) + " (by " + marker + ")")
                ax.set_xlabel("Mark given")
                ax.set_ylabel("# of times assigned")

                base64_histogram_of_grades_m_q.append(gds.get_graph_as_base64(fig))

            base64_histogram_of_grades_m.append(base64_histogram_of_grades_m_q)

            check_num_figs()

        # histogram of time taken to mark each question
        print("Generating histograms of time spent marking each question.")
        max_time = gds.get_ta_df()["seconds_spent_marking"].max()
        bin_width = 15  # seconds
        base64_histogram_of_time = []
        marking_times_for_questions = gds.get_times_for_all_questions()
        for i, question in enumerate(marking_times_for_questions):
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)
            bins = [t / 60.0 for t in range(0, max_time + bin_width, bin_width)]

            ax.hist(
                marking_times_for_questions[question].divide(60),
                bins=bins,
                ec="black",
                alpha=0.5,
            )
            ax.set_title("Time spent marking Q" + str(i + 1))
            ax.set_xlabel("Time spent (min)")
            ax.set_ylabel("# of papers")

            base64_histogram_of_time.append(gds.get_graph_as_base64(fig))

            check_num_figs()

        # scatter plot of time taken to mark each question vs mark given
        print("Generating scatter plots of time spent marking vs mark given.")
        base64_scatter_of_time = []
        for question in spec["question"]:
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

            times_for_question = ta_times.loc[
                ta_times["question_number"] == int(question), "seconds_spent_marking"
            ].div(60)
            mark_given_for_question = ta_grading.loc[
                ta_grading["question_number"] == int(question), "score_given"
            ]

            ax.scatter(
                times_for_question, mark_given_for_question, ec="black", alpha=0.5
            )
            ax.set_title("Q" + str(question) + ": Time spent vs Mark given")
            ax.set_ylabel("Time spent (min)")
            ax.set_xlabel("Mark given")

            base64_scatter_of_time.append(gds.get_graph_as_base64(fig))

            check_num_figs()

        # 1D scatter plot of the average grades given by each marker for each question
        print("Generating 1D scatter plots of average grades for each question.")
        base_64_scatter_of_avgs = []
        for question in spec["question"]:
            fig, ax = plt.subplots(figsize=(3.2, 1.6), tight_layout=True)

            avgs = []
            markers = ["Average"]
            markers.extend(
                ta_grading.loc[
                    ta_grading["question_number"] == int(question), "user"
                ].unique()
            )
            avg_for_question = ta_grading.loc[
                ta_grading["question_number"] == int(question), "score_given"
            ].mean()
            avgs.append(avg_for_question)
            for marker in markers[1:]:
                avgs.append(
                    ta_grading.loc[
                        (ta_grading["question_number"] == int(question))
                        & (ta_grading["user"] == marker),
                        "score_given",
                    ].mean()
                )

            ax.scatter(avgs, np.zeros_like(avgs), ec="black", alpha=0.5)
            ax.set_xlabel("Q" + str(question) + " average marks given")
            ax.tick_params(
                axis="y",
                which="both",  # both major and minor ticks are affected
                left=False,  # ticks along the bottom edge are off
                right=False,  # ticks along the top edge are off
                labelleft=False,
            )
            for i, marker in enumerate(markers):
                ax.annotate(
                    marker,
                    (avgs[i], 0),
                    ha="left",
                    rotation=60,
                )

            plt.xlim(
                [
                    0,
                    ta_grading.loc[
                        ta_grading["question_number"] == int(question), "max_score"
                    ].max(),
                ]
            )
            plt.ylim([-0.1, 1])

            base_64_scatter_of_avgs.append(gds.get_graph_as_base64(fig))

            check_num_figs()

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
        <img src="data:image/png;base64,{base64_histogram_of_grades}">
        <br>
        <p style="break-before: page;"></p>
        <h3>Histograms of grades by question</h3>
        """

        for i, hist in enumerate(base64_histogram_of_grades_q):
            odd = i % 2
            if not odd:
                html += f"""
                <div class="row">
                """
            html += f"""
            <div class="col" style="margin-left:0mm;">
            <img src="data:image/png;base64,{hist}" width="50px" height="40px">
            </div>
            """

            if odd:
                html += f"""
                </div>
                """
        if not odd:
            html += f"""
            </div>
            """

        html += f"""
        <p style="break-before: page;"></p>
        <h3>Correlation heatmap</h3>
        <img src="data:image/png;base64,{base64_corr}">
        </body>
        <p style="break-before: page;"></p>
        <h3>Histograms of grades given by marker</h3>
        """

        for index, marker in enumerate(marks_by_tas):
            html += f"""
            <h4>Grades by {marker}</h4>
            """
            for i, hist in enumerate(base64_histogram_of_grades_m[index]):
                odd = i % 2
                if not odd:
                    html += f"""
                    <div class="row">
                    """
                html += f"""
                <div class="col" style="margin-left:0mm;">
                <img src="data:image/png;base64,{hist}" width="50px" height="40px">
                </div>
                """

                if odd:
                    html += f"""
                    </div>
                    """
            if not odd:
                html += f"""
                </div>
                """

        html += f"""
        <br>
        <p style="break-before: page;"></p>
        <h3>Histograms of time spent marking each question (in seconds)</h3>
        """

        for i, hist in enumerate(base64_histogram_of_time):
            odd = i % 2
            if not odd:
                html += f"""
                <div class="row">
                """
            html += f"""
            <div class="col" style="margin-left:0mm;">
            <img src="data:image/png;base64,{hist}" width="50px" height="40px">
            </div>
            """

            if odd:
                html += f"""
                </div>
                """
        if not odd:
            html += f"""
            </div>
            """

        html += f"""
        <br>
        <p style="break-before: page;"></p>
        <h3>Scatter plots of time spent marking each question vs mark given</h3>
        """

        for i, hist in enumerate(base64_scatter_of_time):
            odd = i % 2
            if not odd:
                html += f"""
                <div class="row">
                """
            html += f"""
            <div class="col" style="margin-left:0mm;">
            <img src="data:image/png;base64,{hist}" width="50px" height="40px">
            </div>
            """

            if odd:
                html += f"""
                </div>
                """
        if not odd:
            html += f"""
            </div>
            """

        html += f"""
        <br>
        <p style="break-before: page;"></p>
        <h3>1D scatter plots of average grades given by each marker for each question</h3>
        """

        for i, hist in enumerate(base_64_scatter_of_avgs):
            odd = i % 2
            if not odd:
                html += f"""
                <div class="row">
                """
            html += f"""
            <div class="col" style="margin-left:0mm;">
            <img src="data:image/png;base64,{hist}" width="50px" height="40px">
            </div>
            """

            if odd:
                html += f"""
                </div>
                """
        if not odd:
            html += f"""
            </div>
            """

        html += f"""
        <br>
        <p style="break-before: page;"></p>
        """

        def create_pdf(html):
            """Generate a PDF file from a string of HTML."""
            htmldoc = HTML(string=html, base_url="")
            # with open("styles.css", "r") as f:
            #     css = f.read()

            return htmldoc.write_pdf(
                stylesheets=[CSS("./static/css/generate_report.css")]
            )

        def save_pdf_to_disk(pdf_data, file_path):
            """Save the PDF data to a file."""
            with open(file_path, "wb") as f:
                f.write(pdf_data)

        date_filename = ""  # dt.datetime.now().strftime("%Y-%m-%d--%H-%M-%S+00-00")
        filename = "Report-" + name + "--" + date_filename + ".pdf"
        print("Writing to " + filename + ".")

        pdf_data = create_pdf(html)
        save_pdf_to_disk(pdf_data, filename)

        print("Finished saving report.")
