# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Colin B. Macdonald
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe

"""
Gather reassembled papers with html page for digital return.
"""

__copyright__ = "Copyright (C) 2018-2020 Colin B. Macdonald and others"
__credits__ = ["The Plom Project Developers"]
__license__ = "AGPL-3.0-or-later"

import os
import sys
import shutil
from pathlib import Path

from plom import SpecParser
from plom.rules import isValidStudentNumber, StudentIDLength
from plom.finish import CSVFilename
from .return_tools import csv_add_return_codes


def do_renaming(fromdir, todir, sns):
    print("Searching for foo_<studentnumber>.pdf files in {0}...".format(fromdir))
    todir = Path(todir)
    fromdir = Path(fromdir)
    numfiles = 0
    for file in os.scandir(fromdir):
        if file.name.endswith(".pdf"):
            oldname = file.name.partition(".")[0]
            sn = oldname.split("_")[-1]
            assert isValidStudentNumber(sn)
            code = sns[sn]
            newname = "{0}_{1}.pdf".format(oldname, code)
            newname = todir / newname
            print(
                '  found SN {0}: code {1}, copying "{2}" to "{3}"'.format(
                    sn, code, file.name, newname
                )
            )
            shutil.copyfile(fromdir / file.name, newname)
            numfiles += 1
    return numfiles


def main(use_hex, digits):
    """Make the secret codes and the return-code webpage.

    args:
        use_hex (bool): use random hex digits, otherwise an integer
            without leading zeros.
        digits (int): length of secret code.
    """
    spec = SpecParser().spec
    shortname = spec["name"]
    longname = spec["longName"]
    codedReturnDir = Path("codedReturn")

    reassembles = ["reassembled", "reassembled_ID_but_not_marked"]
    if os.path.isdir(reassembles[0]) and os.path.isdir(reassembles[1]):
        print('You have more than one "reassembled*" directory:')
        print("  decide what you trying to do and run me again.")
        sys.exit(2)
    elif os.path.isdir(reassembles[0]):
        fromdir = reassembles[0]
    elif os.path.isdir(reassembles[1]):
        fromdir = reassembles[1]
    else:
        print("I cannot find any of the dirs: " + ", ".join(reassembles))
        print("  Have you called the `reassemble` command yet?")
        sys.exit(3)
    print('We will take pdf files from "{0}".'.format(fromdir))

    if codedReturnDir.exists() or os.path.exists("return_codes.csv"):
        print(
            'Directory "{}" and/or "return_codes.csv" already exist:\n'
            "  if you want to re-run this script, delete them first.".format(
                codedReturnDir
            )
        )
        sys.exit(4)
    os.makedirs(codedReturnDir)

    print("Generating return codes spreadsheet...")
    sns = csv_add_return_codes(
        CSVFilename, "return_codes.csv", "StudentID", use_hex, digits
    )
    print('The return codes are in "return_codes.csv"')

    numfiles = do_renaming(fromdir, codedReturnDir, sns)
    if numfiles > 0:
        print("Copied (and renamed) {0} files".format(numfiles))
    else:
        print('no pdf files in "{0}"?  Stopping!'.format(fromdir))
        sys.exit(5)

    print("Adding index.html file")
    from .html_view_test_template import html

    html = html.replace("__COURSENAME__", longname)
    html = html.replace("__TESTNAME__", shortname)
    html = html.replace("__CODE_LENGTH__", str(digits))
    html = html.replace("__SID_LENGTH__", str(StudentIDLength))

    with open(codedReturnDir / "index.html", "w") as htmlfile:
        htmlfile.write(html)

    print("All done!  Next tasks:")
    print('  * Copy "{}" to your webserver'.format(codedReturnDir))
    print('  * Privately communicate info from "return_codes.csv"')
    print("      - E.g., see `contrib/plom-return_codes_to_canvas_csv.py`")
    print("  * Read docs about the security implications of all this.")
