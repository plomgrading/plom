# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import base64
import datetime as dt
from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from weasyprint import HTML, CSS

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from Finish.services import StudentMarkService, TaMarkingService
from Mark.models import MarkingTask
from Papers.models import Specification

RANGE_BIN_OFFSET = 2


class Command(BaseCommand):
    """Generates a PDF report of the marking progress."""

    help = "Generates a PDF report of the marking progress."
    matplotlib.use("Agg")

    def handle(self, *args, **options):
        print("Building report.")

        sms = StudentMarkService()
        tms = TaMarkingService()
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

        # histogram of grades
        print("Generating histogram of grades.")
        fig, ax = plt.subplots()

        ax.hist(marks["total_mark"], bins=range(0, totalMarks + RANGE_BIN_OFFSET))
        ax.set_title("Histogram of Total Marks")
        ax.set_xlabel("Total Mark")
        ax.set_ylabel("Number of Students")

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

            ax.hist(marks_for_question, bins=bins)
            ax.set_title("Histogram of Q" + str(question) + " Marks")
            ax.set_xlabel("Question " + str(question) + " Mark")
            ax.set_ylabel("Number of Students")

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
        marks_corr.columns = marks_corr.columns.str.split("_").str[0]
        marks_corr.index = marks_corr.index.str.split("_").str[0]

        plt.figure(figsize=(6.4, 5.12))
        sns.heatmap(marks_corr, annot=True, cmap="coolwarm")
        plt.title("Correlation between questions")

        png_bytes = BytesIO()
        plt.savefig(png_bytes, format="png")
        png_bytes.seek(0)

        base64_corr = base64.b64encode(png_bytes.read()).decode()
        plt.close("all")

        # histogram of grades given by each marker
        print("Generating histograms of grades given by marker.")
        base64_histogram_of_grades_m = []
        max_score = ta_grading["max_score"].max()
        for marker in ta_grading["user"].unique():
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

            max_score_unique = ta_grading.loc[
                ta_grading["user"] == marker, "max_score"
            ].max()
            scores_given_for_user = ta_grading.loc[
                ta_grading["user"] == marker, "score_given"
            ]
            bins = range(0, max_score_unique + RANGE_BIN_OFFSET)

            ax.hist(scores_given_for_user, bins=bins)
            ax.set_title("(rel) Grades by " + marker)
            ax.set_xlabel("Mark Given")
            ax.set_ylabel("Times Assigned")

            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)

            base64_histogram_of_grades_m.append(
                base64.b64encode(png_bytes.read()).decode()
            )

            plt.close()
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

            bins = range(0, max_score + RANGE_BIN_OFFSET)

            ax.hist(scores_given_for_user, bins=bins)
            ax.set_title("Grades by " + marker)
            ax.set_xlabel("Mark Given")
            ax.set_ylabel("Times Assigned")

            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)

            base64_histogram_of_grades_m.append(
                base64.b64encode(png_bytes.read()).decode()
            )
            plt.close()

        # histogram of time taken to mark each question
        print("Generating histograms of time spent marking each question.")
        max_time = ta_times["seconds_spent_marking"].max()
        bin_width = 5
        base64_histogram_of_time = []
        for question in spec["question"]:
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)

            marking_times_for_question = ta_times.loc[
                ta_times["question_number"] == int(question), "seconds_spent_marking"
            ]
            bins = range(0, max_time + bin_width, bin_width)

            ax.hist(marking_times_for_question, bins=bins)
            ax.set_title("Time spent marking Q" + str(question))
            ax.set_xlabel("Time Taken")
            ax.set_ylabel("Number of Papers")

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
            ]
            mark_given_for_question = ta_grading.loc[
                ta_grading["question_number"] == int(question), "score_given"
            ]

            ax.scatter(times_for_question, mark_given_for_question)
            ax.set_title("Q" + str(question) + ": Time Spent vs Mark Given")
            ax.set_xlabel("Time Taken")
            ax.set_ylabel("Mark Given")

            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)

            base64_scatter_of_time.append(base64.b64encode(png_bytes.read()).decode())
            plt.close()

        html = f"""
        <body>
        <h2>{longName} report</h2>
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
