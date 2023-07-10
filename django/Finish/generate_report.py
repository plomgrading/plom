# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import cm, inch

import datetime as dt

import django
django.setup()

from Papers.models import Specification

spec = Specification.load().spec_dict

print("Writing to hello_plom.pdf")

canvas = Canvas("hello_plom.pdf", pagesize=LETTER)
canvas.setFont("Times-Roman", 12)
canvas.setTitle("Plom Report")

canvas.drawString(2 * inch, 9 * inch, "You are at the mercy of the plom overlords!")
string_out = "name: " + spec["name"] 
canvas.drawString(2 * inch, 8 * inch, string_out)
string_out = "longName: " + spec["longName"]
canvas.drawString(2 * inch, 7.75 * inch, string_out)
string_out = "totalMarks: " + str(spec["totalMarks"])
canvas.drawString(2 * inch, 7.5 * inch, string_out)

string_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S+00:00")
canvas.drawString(2 * inch, 7 * inch, string_time)

print("Finished writing to hello_plom.pdf")

canvas.save()

print("Finished saving hello_plom.pdf")