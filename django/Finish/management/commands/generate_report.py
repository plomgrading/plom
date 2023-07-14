# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import base64
import datetime as dt
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from weasyprint import HTML, CSS

from django.core.management.base import BaseCommand

from Finish.services import StudentMarkService, TaMarkingService
from Mark.models import MarkingTask
from Papers.models import Specification


class Command(BaseCommand):
    """Generates a PDF report of the marking progress."""

    help = "Generates a PDF report of the marking progress."

    def handle(self, *args, **options):
        print("Building report.")

        sms = StudentMarkService()
        tms = TaMarkingService()
        spec = Specification.load().spec_dict
        # for question in spec["question"]:
        #     print(question)
        #     print(spec["question"][question]["mark"])

        student_df = sms.get_all_students_download()
        keys = sms.get_csv_header(spec)
        marks = pd.DataFrame(student_df, columns=keys)

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
        fig, ax = plt.subplots()
        ax.hist(marks["total_mark"], bins=range(0, totalMarks + 1))
        ax.set_title("Histogram of Total Marks")
        ax.set_xlabel("Total Mark")
        ax.set_ylabel("Number of Students")
        png_bytes = BytesIO()
        fig.savefig(png_bytes, format="png")
        # encode the bytes as a base64 string
        png_bytes.seek(0)
        base64_histogram_of_grades = base64.b64encode(png_bytes.read()).decode()

        # histogram of grades for each question
        base64_histogram_of_grades_q = []
        for question in spec["question"]:
            fig, ax = plt.subplots(figsize=(3.2, 2.4), tight_layout=True)
            ax.hist(
                marks["q" + str(question) + "_mark"],
                bins=range(0, spec["question"][question]["mark"] + 1),
            )
            ax.set_title("Histogram of Question " + str(question) + " Marks")
            ax.set_xlabel("Question " + str(question) + " Mark")
            ax.set_ylabel("Number of Students")
            png_bytes = BytesIO()
            fig.savefig(png_bytes, format="png")
            png_bytes.seek(0)
            base64_histogram_of_grades_q.append(
                base64.b64encode(png_bytes.read()).decode()
            )

        # correlation heatmap
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

        # table for report
        marks = marks[["student_id", "student_name", "paper_number", "total_mark"]]
        table = marks.to_html()

        html = f"""
        <body>
        <h2>{longName} report</h2>
        <p>date: {date}</p>
        <br>
        <h4>Overview</h4>
        <p>Number of students: {num_students}</p>
        <p>Average total mark: {average_mark:.2f}/{totalMarks}</p>
        <p>Median total mark: {median_mark}/{totalMarks}</p>
        <p>Standard deviation of total marks: {stdev_mark:.2f}</p>
        <br>
        <img src="data:image/png;base64,{base64_histogram_of_grades}">
        <br>
        <p style="break-before: page;"></p>
        <h4>Histograms by question</h4>
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
        <br>
        <p style="break-before: page;"></p>
        <h4>Correlation heatmap</h4>
        <img src="data:image/png;base64,{base64_corr}">
        </body>
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

        print("Writing to hello_plom.pdf")

        pdf_data = create_pdf(html)
        save_pdf_to_disk(pdf_data, "hello_plom.pdf")

        print("Finished saving hello_plom.pdf")
