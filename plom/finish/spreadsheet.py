# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020-2023 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2023 Julian Lapenna

import arrow
import csv

from plom import get_question_label
from plom.finish import with_finish_messenger
from plom.finish import CSVFilename


def write_spreadsheet(spreadSheetDict, labels, filename):
    """Writes all of the current marks to a local csv file.

    Arguments:
        spreadSheetDict (dict): Dictionary containing the tests to be
            written to a spreadsheet.
        labels (list): string labels for each question.
        filename (pathlib.Path/str): where to save the csv.

    Returns:
        tuple: Two booleans, the first is False if each test in
        spreadSheetDict is marked, True otherwise . The second
        is False if there is a test with no ID, True otherwise.
    """
    head = ["StudentID", "StudentName", "TestNumber"]
    # Note: csv library seems smart enough to escape the labels (comma, quotes, etc)
    for label in labels:
        head.append(f"{label} mark")
    head.append("Total")
    for label in labels:
        head.append(f"{label} version")
    head.append("LastUpdate")  # last time any part of the test was updated on server
    head.append("CSVWriteTime")  # when the test's row written in this csv file.
    head.append("Warnings")

    with open(filename, "w") as csvfile:
        testWriter = csv.DictWriter(
            csvfile,
            fieldnames=head,
            quotechar='"',
            quoting=csv.QUOTE_NONNUMERIC,
        )
        testWriter.writeheader()
        existsUnmarked = False
        existsMissingID = False
        for t, thisTest in spreadSheetDict.items():
            if thisTest["marked"] is False:
                existsUnmarked = True  # Check for unmarked tests as to return the appropriate warning
            row = {}
            row["StudentID"] = thisTest["sid"]
            row["StudentName"] = thisTest["sname"]
            row["TestNumber"] = int(t)
            tot = 0
            for i, label in enumerate(labels):
                q = i + 1
                if thisTest["marked"]:
                    tot += int(thisTest["q{}m".format(q)])
                row[f"{label} mark"] = thisTest["q{}m".format(q)]
                row[f"{label} version"] = thisTest["q{}v".format(q)]
            if thisTest["marked"]:
                row["Total"] = tot
            else:
                row["Total"] = ""

            lu = arrow.get(thisTest["last_update"])
            row["LastUpdate"] = lu.isoformat(" ", "seconds")
            row["CSVWriteTime"] = arrow.utcnow().isoformat(" ", "seconds")

            warnString = ""
            if not thisTest["identified"]:
                warnString += "[Unidentified]"
            if "Blank" in thisTest["sname"]:
                warnString += "[Blank ID]"
                existsMissingID = True
            if "No ID" in thisTest["sname"]:
                warnString += "[No ID]"
                existsMissingID = True
            if not thisTest["marked"]:
                warnString += "[Unmarked]"
            row["Warnings"] = warnString

            testWriter.writerow(row)

    return existsUnmarked, existsMissingID


@with_finish_messenger
def pull_spreadsheet(*, msgr, filename=CSVFilename, verbose=True):
    """Download the "marks.csv" spreadsheet from the server, optionally printing status messages.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
        filename (pathlib.Path/str): where to save the csv, defaults
            to "marks.csv".
        verbose (bool): echo diagnostics to stdout, default True.

    Returns:
        bool: True if all grading is complete and identified.  False if
        grading is incomplete or some papers are not IDed.  Note in
        either case we write the spreadsheet.
    """
    spec = msgr.get_spec()
    numberOfQuestions = spec["numberOfQuestions"]
    spreadSheetDict = msgr.RgetSpreadsheet()

    qlabels = [get_question_label(spec, n + 1) for n in range(numberOfQuestions)]
    existsUnmarked, existsMissingID = write_spreadsheet(
        spreadSheetDict, qlabels, filename
    )
    if verbose:
        if existsUnmarked:
            print(f'Partial marks written to "{filename}" (marking is not complete).')
        else:
            print(f'Marks written to "{filename}".')
        if existsMissingID:
            print("Warning: not every test is identified.")
    return not existsUnmarked and not existsMissingID
