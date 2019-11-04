#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gather reassembled papers with html page for digital return.
"""

__author__ = "Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2019 Colin B. Macdonald"
__credits__ = ["Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os, sys, shutil

from utils import myhash, SALTSTR as saltstr

# check saltstr is set to something other than "salt"
if saltstr == "salt":
    print(
        'You need to edit utils.py and change SALTSTR to something other than "salt".'
    )
    print("Rerun this script after you have done that.")
    exit()

# TODO: should get this from project, something like 'Math 253 Midterm 2'
longname = "Math Exam"  # bland default for now


def do_renaming(fromdir, todir):
    print("Searching for foo_<studentnumber>.pdf files in {0}...".format(fromdir))
    numfiles = 0
    for file in os.scandir(fromdir):
        if file.name.endswith(".pdf"):
            oldname = file.name.partition(".")[0]
            sn = oldname[-8:]
            assert len(sn) == 8
            assert sn.isdigit()
            code = myhash(sn)
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


if __name__ == "__main__":
    # this allows us to import from ../resources
    sys.path.append("..")
    from resources.testspecification import TestSpecification

    print('Salt is "{0}"'.format(saltstr))

    spec = TestSpecification()
    spec.readSpec()
    shortname = spec.Name

    # TODO: but "reassembed" is created even if I use 09alt
    reassembles = ["reassembled", "reassembled_ID_but_not_marked"]
    if os.path.isdir(reassembles[0]) and os.path.isdir(reassembles[1]):
        print('You have more than one "reassembled*" directory:')
        print("  decide what you trying to do and run me again.")
        sys.exit()
    elif os.path.isdir(reassembles[0]):
        fromdir = reassembles[0]
    elif os.path.isdir(reassembles[1]):
        fromdir = reassembles[1]
    else:
        print("I cannot find any of the dirs: " + ", ".join(reassembles))
        print('  Have you called one of the "09" scripts first?')
        sys.exit()
    print('Going to take pdf files from "{0}".'.format(fromdir))

    try:
        os.mkdir("codedReturn")
    except FileExistsError:
        print(
            'Directory "codedReturn" already exists: if you want to re-run this script, try deleting it first.'
        )
        sys.exit()

    numfiles = do_renaming(fromdir, "codedReturn")
    if numfiles > 0:
        print("renamed and copied {0} files".format(numfiles))
    else:
        print('no pdf files in "{0}"?  Stopping!'.format(fromdir))
        sys.exit()

    print("Adding codedReturn/index.html file")
    with open("view_test_template.html", "r") as htmlfile:
        html = htmlfile.read()
    html = html.replace("__COURSENAME__", longname)
    html = html.replace("__TESTNAME__", shortname)

    newname = os.path.join("codedReturn", "index.html")
    with open(newname, "w") as htmlfile:
        htmlfile.write(html)

    print("All done!  Next tasks:")
    print('  copy "codedReturn/" to your webserver')
    print("  run 11_write_to_canvas_spreadsheet.py and upload to canvas")
