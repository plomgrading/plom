# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2018 Elvis Cai
# Copyright (C) 2019-2020, 2022 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Liam Yih

from plom.misc_utils import local_now_to_simple_string


def makeCover(test_num, sname, sid, tab, pdfname, solution=False):
    """Create html page of name ID etc and table of marks.

    Args:
        test_num (int): the test number for the test we are making the cover for.
        sname (str): student name.
        sid (str): student id.
        tab (list): information about the test that should be put on the coverpage.
        pdfname (pathlib.Path): filename to save the pdf into
        solution (bool): whether or not this is a cover page for solutions
    """
    # hide imports until needed Issue #2231.
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

    htmlText = "<html><body>\n"
    if solution:
        htmlText += "<h3>Solutions</h3>\n"
    else:
        htmlText += "<h3>Results</h3>\n"
    htmlText += """
<ul>
  <li>Name = {}</li>
  <li>ID = {}</li>
  <li>Test number = {}</li>
</ul>
<table>""".format(
        sname, sid, test_num
    )
    if solution:
        htmlText += "<tr><th>question</th><th>version</th><th>mark out of</th></tr>\n"
    else:
        htmlText += (
            "<tr><th>question</th><th>version</th><th>mark</th><th>out of</th></tr>\n"
        )
    # Start computing total mark.
    totalMark = 0
    maxPossible = 0
    for y in tab:
        totalMark += y[2] if y[2] is not None else 0
        maxPossible += y[3]
        # Row of mark table with Group, Version, Mark, MaxPossibleMark
        g, v, m, x = y

        if solution:  # ignore 'Mark'
            htmlText += f"<tr><td>{g}</td><td>{v}</td><td>{x}</td></tr>\n"
        else:
            htmlText += f"<tr><td>{g}</td><td>{v}</td><td>{m}</td><td>{x}</td></tr>\n"

    # Final total mark out of maxPossible total mark.
    if solution:
        htmlText += f"<tr><td>total</td><td>&middot;</td><td>{maxPossible}</td>\n"
    else:
        htmlText += (
            "<tr><td>total</td><td>&middot;</td><td>{}</td><td>{}</td>\n".format(
                totalMark, maxPossible
            )
        )
    htmlText += """
    </table>
    <footer style="position:absolute; bottom:0;">
    """
    htmlText += """
    Coverpage produced on {}
    </ul>
    </footer>
    """.format(
        local_now_to_simple_string()
    )
    htmlText += """
</body>
</html>"""
    # Pipe the htmltext into weasyprint.
    cover = HTML(string=htmlText)
    cover.write_pdf(pdfname, stylesheets=[css])
