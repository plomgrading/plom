# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import base64
import datetime as dt
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
from weasyprint import HTML, CSS

import django

django.setup()

from Finish.services import StudentMarkService, TaMarkingService
from Mark.models import MarkingTask
from Papers.models import Specification

print("Building report.")

sms = StudentMarkService()
tms = TaMarkingService()
spec = Specification.load().spec_dict

student_df = sms.get_all_students_download()
keys = sms.get_csv_header(spec)
marks = pd.DataFrame(student_df, columns=keys)


# INFO FOR REPORT
name = spec["name"]
longName = spec["longName"]
totalMarks = spec["totalMarks"]
date = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S+00:00")
num_students = (
    MarkingTask.objects.values_list("paper__paper_number", flat=True).distinct().count()
)
average_mark = marks["total_mark"].mean()
median_mark = marks["total_mark"].median()

# IMAGE FOR REPORT
fig, ax = plt.subplots()
ax.hist(marks["total_mark"], bins=range(0, totalMarks + 1))
ax.set_title("Histogram of Total Marks")
ax.set_xlabel("Total Mark")
ax.set_ylabel("Number of Students")
png_bytes = BytesIO()
fig.savefig(png_bytes, format="png")

# encode the bytes as a base64 string
png_bytes.seek(0)
base64_string = base64.b64encode(png_bytes.read()).decode()

# TABLE FOR REPORT
marks = marks[["student_id", "student_name", "paper_number", "total_mark"]]
table = marks.to_html()

html = f"""
<body>
<h2>{longName} report</h2>
<p>date: {date}</p>
<br>
<p>number of students: {num_students}</p>
<p>average mark: {average_mark:.2f}/{totalMarks}</p>
<p>median mark: {median_mark}/{totalMarks}</p>
<br>
<img src="data:image/png;base64,{base64_string}" alt="Histogram of Total Marks">
<br>
<p style="break-before: page;"></p>
{table}
</body>
"""


# DO NOT CHANGE THE FOLLOWING TWO FUNCTIONS
def create_pdf(html):
    """Generate a PDF file from a string of HTML."""
    htmldoc = HTML(string=html, base_url="")
    return htmldoc.write_pdf(
        stylesheets=[
            CSS(
                string="""
                @page {
                    @top-left {
                        content     : "Made with";
                        margin-left : 125mm;
                        margin-top  : 10mm;
                    }
                    @top-right {
                        content         : "";
                        width           : 119px;
                        height          : 40px;
                        margin-right    : -10mm;
                        background      : url('https://plomgrading.org/images/plomLogo.png');
                        background-size : 100%;
                    }
                }"""
            )
        ]
    )


def save_pdf_to_disk(pdf_data, file_path):
    """Save the PDF data to a file."""
    with open(file_path, "wb") as f:
        f.write(pdf_data)


print("Writing to hello_plom.pdf")

pdf_data = create_pdf(html)
save_pdf_to_disk(pdf_data, "hello_plom.pdf")

print("Finished saving hello_plom.pdf")
