# -*- coding: utf-8 -*-

"""
Gather reassembled papers with html page for digital return.
"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2020 Colin B. Macdonald"
__credits__ = ["The Plom Project Developers"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os, sys, shutil
import argparse

from plom import SpecParser
from plom.rules import isValidStudentNumber
from .utils import myhash
from .return_tools import csv_add_return_codes


def do_renaming(fromdir, todir, saltstr):
    # TODO: rather than scraping reassembled/ maybe we should work from the DB
    print("Searching for foo_<studentnumber>.pdf files in {0}...".format(fromdir))
    numfiles = 0
    for file in os.scandir(fromdir):
        if file.name.endswith(".pdf"):
            oldname = file.name.partition(".")[0]
            sn = oldname.split("_")[-1]
            assert isValidStudentNumber(sn)
            code = myhash(sn, saltstr)
            newname = "{0}_{1}.pdf".format(oldname, code)
            newname = os.path.join(todir, newname)
            print(
                '  found SN {0}: code {1}, copying "{2}" to "{3}"'.format(
                    sn, code, file.name, newname
                )
            )
            shutil.copyfile(os.path.join(fromdir, file.name), newname)
            numfiles += 1
    return numfiles


def main(saltstr=None):
    # TODO: more docs
    # If you know the salt string and you know someone's student
    # number, you can determine their code.  You should set this
    # per course (not per test).

    if not saltstr:
        raise ValueError("You must set the Salt String")

    spec = SpecParser().spec
    shortname = spec["name"]
    longname = spec["longName"]

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

    if os.path.exists("codedReturn") or os.path.exists("return_codes.csv"):
        print(
            'Directory "codedReturn" and/or "return_codes.csv" already exist:\n'
            "  if you want to re-run this script, delete them first."
        )
        sys.exit(4)
    os.makedirs("codedReturn")

    print("Generating return codes spreadsheet...")
    sns = csv_add_return_codes(
        "testMarks.csv", "return_codes.csv", saltstr, "StudentID"
    )
    print('The return codes are in "return_codes.csv"')

    numfiles = do_renaming(fromdir, "codedReturn", saltstr)
    if numfiles > 0:
        print("Copied (and renamed) {0} files".format(numfiles))
    else:
        print('no pdf files in "{0}"?  Stopping!'.format(fromdir))
        sys.exit(5)

    print("Adding codedReturn/index.html file")
    from .html_view_test_template import html
    html = html.replace("__COURSENAME__", longname)
    html = html.replace("__TESTNAME__", shortname)

    newname = os.path.join("codedReturn", "index.html")
    with open(newname, "w") as htmlfile:
        htmlfile.write(html)

    print("All done!  Next tasks:")
    print('  * Copy "codedReturn/" to your webserver')
    print('  * Privately communicate info from "return_codes.csv"')
    print("      - E.g., try `11_write_to_canvas_spreadsheet`")
    print("        (warning: beta!) and update to Canvas.")
    print("  * Read docs about the security implications of all this.")


if __name__ == "__main__":
    main()
