# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2019 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import sys
from weasyprint import HTML, CSS


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


def makeCover(test_num, sname, sid, tab):
    """Create html page of name ID etc and table of marks.

    Args:
        test_num (int): the test number for the test we are making the cover for.
        sname (str): student name.
        sid (str): student id.
        tab (list): information about the test that should be put on the coverpage.
    """
    htmlText = """
<html>
<body>
<h3>Results</h3>
<ul>
  <li>Name = {}</li>
  <li>ID = {}</li>
  <li>Test number = {}</li>
</ul>
<table>""".format(
        sname, sid, test_num
    )
    htmlText += (
        "<tr><th>question</th><th>version</th><th>mark</th><th>out of</th></tr>\n"
    )
    # Start computing total mark.
    totalMark = 0
    maxPossible = 0
    for y in tab:
        totalMark += y[2]
        maxPossible += y[3]
        # Row of mark table with Group, Version, Mark, MaxPossibleMark
        htmlText += "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>\n".format(*y)
    # Final total mark out of maxPossible total mark.
    htmlText += "<tr><td>total</td><td>&middot;</td><td>{}</td><td>{}</td>\n".format(
        totalMark, maxPossible
    )
    htmlText += """
</table>
</body>
</html>"""
    # Pipe the htmltext into weasyprint.
    cover = HTML(string=htmlText)
    # Write out the coverpage to PDF call it cover_X.pdf where X=StudentID.
    cover.write_pdf(
        "coverPages/cover_{}.pdf".format(str(test_num).zfill(4)), stylesheets=[css]
    )


if __name__ == "__main__":
    # Take the arguments from the commandline.
    # The args should be
    #   TestNumber, 'The Name', ID
    # and then for a list of lists of 4 numbers for each group:
    #   '[[group, version, mark, maxPossibleMark], [...], [...]]'
    arg = sys.argv[1:]
    # build list of lists
    arg[3] = eval(arg[3])
    makeCover(*arg)
