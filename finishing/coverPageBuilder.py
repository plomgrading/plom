__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai"]
__license__ = "AGPLv3"

import sys
from weasyprint import HTML, CSS

# Take the arguments from the commandline.
# The args should be
# [TestNumber, Name, ID,]
# and then for each group [group, version, mark, maxPossibleMark]
# all as a list.
arg = eval(sys.argv[1])
# A simple CSS header to style the cover page nicely.
css = CSS(
    string="""
@page {
  size: Letter; /* Change from the default size of A4 */
  margin: 2.5cm; /* Set margin on each page */
}
body {
    font-family: sans serif;
}
table, th, td {
    border: 1px solid black;
    border-collapse: collapse;
    padding: 5px;
    text-align: center;
}
"""
)
# Create html page of name ID etc and table of marks
htmlText = "<h3>Results</h3>\n"
htmlText += "<ul>"
htmlText += "<li>Name = {}</li>\n".format(arg[1])
htmlText += "<li>ID = {}</li>\n".format(arg[2])
htmlText += "<li>Test number = {}</li>\n".format(arg[0])
htmlText += "</ul>"
htmlText += "<table>\n"
htmlText += "<tr><th>question</th><th>version</th><th>mark</th><th>out of</th></tr>\n"
# Start computing total mark.
totalMark = 0
maxPossible = 0
for x in range(3, len(arg)):
    y = arg[x]
    totalMark += y[2]
    maxPossible += y[3]
    # Row of mark table with Group, Version, Mark, MaxPossibleMark
    htmlText += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n".format(
        y[0], y[1], y[2], y[3]
    )
# Final total mark out of maxPossible total mark.
htmlText += "<tr><td>total</td><td>&middot;</td><td>{}</td><td>{}</td>\n".format(
    totalMark, maxPossible
)
htmlText += "</table>\n"
# Pipe the htmltext into weasyprint.
cover = HTML(string=htmlText)
# Write out the coverpage to PDF call it cover_X.pdf where X=StudentID.
cover.write_pdf(
    "coverPages/cover_{}.pdf".format(str(arg[0]).zfill(4)), stylesheets=[css]
)
