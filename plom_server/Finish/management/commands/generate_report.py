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

from Finish.services import StudentMarkService, TaMarkingService
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
        average_mark = marks["total_mark"].mean()
        median_mark = marks["total_mark"].median()
        stdev_mark = marks["total_mark"].std()
        total_tasks = mts.get_n_total_tasks()
        all_marked = mts.get_n_marked_tasks() == total_tasks and total_tasks > 0

        # histogram of grades
        print("Generating histogram of grades.")
        fig, ax = plt.subplots()

        ax.hist(
            marks["total_mark"],
            bins=range(0, totalMarks + RANGE_BIN_OFFSET),
            ec="black",
            alpha=0.5,
        )
        ax.set_title("Histogram of total marks")
        ax.set_xlabel("Total mark")
        ax.set_ylabel("# of students")

        # encode the bytes as a base64 string
        png_bytes = BytesIO()
        fig.savefig(png_bytes, format="png")
        png_bytes.seek(0)

        base64_histogram_of_grades = base64.b64encode(png_bytes.read()).decode()
        plt.close()

        # histogram of grades for each question
        print("Generating histograms of grades by question.")
        base64_histogram_of_grades_q = []
        for question in spec["question"]:
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

            marks_for_question = marks["q" + str(question) + "_mark"]
            bins = range(0, spec["question"][question]["mark"] + RANGE_BIN_OFFSET)

            ax.hist(marks_for_question, bins=bins, ec="black", alpha=0.5)
            ax.set_title("Histogram of Q" + str(question) + " marks")
            ax.set_xlabel("Question " + str(question) + " mark")
            ax.set_ylabel("# of students")

            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)

            base64_histogram_of_grades_q.append(
                base64.b64encode(png_bytes.read()).decode()
            )
            plt.close()

        # correlation heatmap
        print("Generating correlation heatmap.")
        marks_corr = marks.copy(deep=True)
        marks_corr = (
            marks_corr.filter(regex="q[0-9]*_mark").corr(numeric_only=True).round(2)
        )

        col_names = []
        for i, col_name in enumerate(marks_corr.columns.str.split("_").str[0]):
            col_names.append("Q" + str(i + 1))

        marks_corr.columns = col_names
        marks_corr.index = col_names

        plt.figure(figsize=(6.4, 5.12))
        sns.heatmap(
            marks_corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, square=True
        )
        plt.title("Correlation between questions")

        png_bytes = BytesIO()
        plt.savefig(png_bytes, format="png")
        png_bytes.seek(0)

        base64_corr = base64.b64encode(png_bytes.read()).decode()
        plt.close("all")

        # histogram of grades given by each marker
        print("Generating histograms of grades given by marker.")
        base64_histogram_of_grades_m = []
        for marker in ta_grading["user"].unique():
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

            scores_given_for_user = (
                ta_grading.loc[ta_grading["user"] == marker, "score_given"]
                / ta_grading.loc[ta_grading["user"] == marker, "max_score"]
            )
            bins = [x / 100 for x in range(0, 120, 10)]

            ax.hist(scores_given_for_user, bins=bins, ec="black", alpha=0.5)
            ax.set_title("(norm) Grades by " + marker)
            ax.set_xlabel("Mark given")
            ax.set_ylabel("# of times assigned")

            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)

            base64_histogram_of_grades_m.append(
                base64.b64encode(png_bytes.read()).decode()
            )

            plt.close()
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)
            scores_given_for_user = ta_grading.loc[
                ta_grading["user"] == marker, "score_given"
            ]
            max_score_for_user = ta_grading.loc[
                ta_grading["user"] == marker, "max_score"
            ].max()
            bins = range(0, max_score_for_user + RANGE_BIN_OFFSET)

            ax.hist(scores_given_for_user, bins=bins, ec="black", alpha=0.5)
            ax.set_title("(abs) Grades by " + marker)
            ax.set_xlabel("Mark given")
            ax.set_ylabel("# of times assigned")

            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)

            base64_histogram_of_grades_m.append(
                base64.b64encode(png_bytes.read()).decode()
            )

        # histogram of time taken to mark each question
        print("Generating histograms of time spent marking each question.")
        max_time = ta_times["seconds_spent_marking"].max()
        bin_width = 15  # seconds
        base64_histogram_of_time = []
        for question in spec["question"]:
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

            marking_times_for_question = ta_times.loc[
                ta_times["question_number"] == int(question), "seconds_spent_marking"
            ].div(60)
            bins = [t / 60.0 for t in range(0, max_time + bin_width, bin_width)]

            ax.hist(marking_times_for_question, bins=bins, ec="black", alpha=0.5)
            ax.set_title("Time spent marking Q" + str(question))
            ax.set_xlabel("Time spent (min)")
            ax.set_ylabel("# of papers")

            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)

            base64_histogram_of_time.append(base64.b64encode(png_bytes.read()).decode())
            plt.close()

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
            ax.set_xlabel("Time spent (min)")
            ax.set_ylabel("Mark given")

            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)

            base64_scatter_of_time.append(base64.b64encode(png_bytes.read()).decode())
            plt.close()

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

            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)

            base_64_scatter_of_avgs.append(base64.b64encode(png_bytes.read()).decode())
            plt.close()

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

        for i, hist in enumerate(base64_histogram_of_grades_m):
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
