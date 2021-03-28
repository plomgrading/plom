# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe

import csv
import getpass

from plom import get_question_label
from plom.messenger import FinishMessenger
from plom.plom_exceptions import PlomExistingLoginException
from plom.finish import CSVFilename


def writeSpreadsheet(spreadSheetDict, labels):
    """Writes all of the current marks to a local csv file.

    Arguments:
        spreadSheetDict (dict): Dictionary containing the tests to be
            written to a spreadsheet.
        labels (list): string labels for each question.

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
    head.append("Warnings")

    with open(CSVFilename, "w") as csvfile:
        testWriter = csv.DictWriter(
            csvfile,
            fieldnames=head,
            quotechar='"',
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


def main(server=None, password=None):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = FinishMessenger(s, port=p)
    else:
        msgr = FinishMessenger(server)
    msgr.start()

    if not password:
        password = getpass.getpass("Please enter the 'manager' password:")

    try:
        msgr.requestAndSaveToken("manager", password)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another finishing-script or manager-client running,\n"
            "    e.g., on another computer?\n\n"
            "In order to force-logout the existing authorization run `plom-finish clear`."
        )
        exit(10)

    try:
        spec = msgr.get_spec()
        numberOfQuestions = spec["numberOfQuestions"]
        spreadSheetDict = msgr.RgetSpreadsheet()
    finally:
        msgr.closeUser()
        msgr.stop()

    qlabels = [get_question_label(spec, n + 1) for n in range(numberOfQuestions)]
    existsUnmarked, existsMissingID = writeSpreadsheet(spreadSheetDict, qlabels)
    if existsUnmarked and existsMissingID:
        print(
            'Partial marks written to "{}" (marking is not complete). Warning: not every test is identified.'.format(
                CSVFilename
            )
        )
    elif existsUnmarked:
        print(
            'Partial marks written to "{}" (marking is not complete)'.format(
                CSVFilename
            )
        )
    elif existsMissingID:
        print(
            'Marks written to "{}". Warning: not every test is identified.'.format(
                CSVFilename
            )
        )
    else:
        print('Marks written to "{}"'.format(CSVFilename))


if __name__ == "__main__":
    main()
