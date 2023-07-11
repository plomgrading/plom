# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

import base64
import datetime as dt
from io import BytesIO
import matplotlib.pyplot as plt
import pandas as pd
from weasyprint import HTML

import django

django.setup()

from Papers.models import Specification, Paper
from Finish.services import StudentMarkService, TaMarkingService

sms = StudentMarkService()
tms = TaMarkingService()
spec = Specification.load().spec_dict

student_marks = sms.get_all_students_download()
keys = sms.get_csv_header(spec)
df = pd.DataFrame(student_marks, columns=keys)

name = spec["name"]
longName = spec["longName"]
totalMarks = spec["totalMarks"]
date = dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S+00:00")
num_students = Paper.objects.count()
average_mark = df["total_mark"].mean()
median_mark = df["total_mark"].median()

# create a matplotlib plot and save it to a BytesIO object
fig, ax = plt.subplots()
ax.hist(df["total_mark"], bins=range(0, totalMarks + 1))
ax.set_title("Histogram of Total Marks")
ax.set_xlabel("Total Mark")
ax.set_ylabel("Number of Students")
png_bytes = BytesIO()
fig.savefig(png_bytes, format="png")

# encode the bytes as a base64 string
png_bytes.seek(0)
base64_string = base64.b64encode(png_bytes.read()).decode()

html = f"""
<h2>{longName} report</h2>
<p>date: {date}</p>
<br>
<p>number of students: {num_students}</p>
<p>average mark: {average_mark:.2f}/{totalMarks}</p>
<p>median mark: {median_mark}/{totalMarks}</p>
<br>
<img src="data:image/png;base64,{base64_string}" alt="Histogram of Total Marks">
"""


def create_pdf(html):
    """Generate a PDF file from a string of HTML."""
    htmldoc = HTML(string=html, base_url="")
    return htmldoc.write_pdf()


def save_pdf_to_disk(pdf_data, file_path):
    """Save the PDF data to a file."""
    with open(file_path, "wb") as f:
        f.write(pdf_data)


print("Writing to hello_plom.pdf")

pdf_data = create_pdf(html)
save_pdf_to_disk(pdf_data, "hello_plom.pdf")

print("Finished saving hello_plom.pdf")
