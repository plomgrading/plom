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
from .utils import myhash


def do_renaming(fromdir, todir, saltstr):
    print("Searching for foo_<studentnumber>.pdf files in {0}...".format(fromdir))
    numfiles = 0
    for file in os.scandir(fromdir):
        if file.name.endswith(".pdf"):
            oldname = file.name.partition(".")[0]
            sn = oldname[-8:]
            assert len(sn) == 8
            assert sn.isdigit()
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
        print("TODO: how can we show help here instead?")
        raise ValueError("You must set the Salt String")

    print('Salt is "{0}"'.format(saltstr))

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
    print('Going to take pdf files from "{0}".'.format(fromdir))

    try:
        os.mkdir("codedReturn")
    except FileExistsError:
        print(
            'Directory "codedReturn" already exists: if you want to re-run this script, try deleting it first.'
        )
        sys.exit(4)

    numfiles = do_renaming(fromdir, "codedReturn", saltstr)
    if numfiles > 0:
        print("renamed and copied {0} files".format(numfiles))
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
    print("  * Try `11_write_to_canvas_spreadsheet` (warning: beta!)")
    print("    and upload the result directly to Canvas.")
    print("  * TODO: add another generic option here about csv")


if __name__ == "__main__":
    main()
