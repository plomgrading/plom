#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2019 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe

"""
Produce a minimal archive of your test.

This is intended for archival purposes.  Note it would not be easy to
regrade a question within Plom using this archive.  If you ever
anticipate revisiting the grading of this test, you should backup the
entire directory structure.

Usage:
$ ./12_archive course year term

for example:
$ ./12_archive math253 2019 S1
"""

__copyright__ = "Copyright (C) 2019-2020 Colin B. Macdonald and others"
__credits__ = ["The Plom Project Developers"]
__license__ = "AGPL-3.0-or-later"

import os
import sys
import shutil

from plom import SpecVerifier
from plom.finish import CSVFilename


archivename = "{COURSE}_{YEAR}{TERM}_{SHORTNAME}"


if __name__ == "__main__":
    spec = SpecVerifier.load_verified()
    basename = spec["name"]
    archivename = archivename.replace("{SHORTNAME}", basename)

    print("\n\nTODO: THIS SCRIPT NEEDS RETHINKING FOR 0.4!\n\n")

    # TODO: someday we can get this from spec file?
    # https://gitlab.com/plom/plom/issues/94
    if not len(sys.argv) == 4:
        print("ERROR: Incorrect command line...")
        print(__doc__)
        sys.exit(1)
    archivename = archivename.replace("{COURSE}", sys.argv[1])
    archivename = archivename.replace("{YEAR}", sys.argv[2])
    archivename = archivename.replace("{TERM}", sys.argv[3])

    print(
        """
This script tries to produce a minimal archive of your test:
    "{0}.zip"
This is intended for archival purposes.  Note it would not be easy to
regrade a question within Plom using this archive.  If you ever
anticipate revisiting the grading of this test, you should backup the
entire directory structure.
    """.format(
            archivename
        )
    )
    # input('Press Enter to continue...')

    all_ok = True

    print('Creating temporary directory "{0}"'.format(archivename))
    try:
        os.mkdir(archivename)
    except FileExistsError:
        print(
            'Directory "{0}" already exists: if you want to re-run this script, try deleting it first.'.format(
                archivename
            )
        )
        sys.exit(1)

    print("Archiving source pdf files")
    try:
        shutil.copytree(
            os.path.join("..", "build", "sourceVersions"),
            os.path.join(archivename, "sourceVersions"),
            symlinks=False,
        )
    except:
        print('  WARNING: could not archive "build/sourceVersions" directory')
        all_ok = False

    print("Archiving raw scans")
    try:
        shutil.copytree(
            os.path.join("..", "scanAndGroup", "scannedExams"),
            os.path.join(archivename, "scannedExams"),
            symlinks=False,
        )
    except:
        print('  WARNING: could not archive "scanAndGroup/scannedExams" directory')
        all_ok = False
    try:
        os.rmdir(os.path.join(archivename, "scannedExams", "png"))
    except:
        print(
            '  WARNING: could not remove supposedly-empty "scanningExams/png" directory'
        )
        all_ok = False

    t1 = os.path.isdir("reassembled")
    t2 = os.path.isdir("reassembled_ID_but_not_marked")
    if t1 and not t2:
        print('Archiving final graded pdf files ("reassembled")')
        shutil.copytree(
            "reassembled", os.path.join(archivename, "reassembled"), symlinks=False
        )
    elif t2 and not t1:
        print('Archiving final identified pdf files ("reassembled_ID_but_not_marked")')
        shutil.copytree(
            "reassembled_ID_but_not_marked",
            os.path.join(archivename, "reassembled_ID_but_not_marked"),
            symlinks=False,
        )
    elif t1 and t2:
        print(
            "  WARNING: found both reassembled and reassembled_ID_but_not_marked directories. Which should be archived?"
        )
        all_ok = False
    else:
        print("  WARNING: cannot find any reassembled papers.")
        all_ok = False

    print("Archiving metadata and miscellanea")
    shutil.copy2(CSVFilename, archivename)
    shutil.copy2(os.path.join("..", "resources", "testSpec.json"), archivename)
    # which version was used for each exam number
    shutil.copy2(os.path.join("..", "resources", "examsProduced.json"), archivename)
    # the mapping b/w scan file and paper number
    shutil.copy2(os.path.join("..", "resources", "examsScanned.json"), archivename)
    # the mapping b/w paper number and student
    shutil.copy2(os.path.join("..", "resources", "examsIdentified.json"), archivename)
    # who did the marking
    shutil.copy2(os.path.join("..", "resources", "groupImagesMarked.json"), archivename)
    # TODO: information about grading times?

    with open(os.path.join(archivename, "README.txt"), "w") as file:
        file.write(
            """Plom Archive File
=================

Explanations:

  * reassembled: these are the final graded pdf files, by student number.

  * reassembled_ID_but_not_marked: these are the final identified (but not marked) pdf files, by student number. This probably means the marking was done on-paper before the papers were scanned. Note that only one of "reassembled" and "reassembled_ID_but_not_marked" should be present.

  * sourceVersions: the original blank pdfs for the test/exam.  Each
    student's test is some combination of these.

  * scannedExams: the raw unmarked files directly from the scanner.

  * The various .json files can be used to find students' papers in the raw
    scans.
"""
        )

    print("Creating zip file")
    fn = shutil.make_archive(archivename, "zip", base_dir=archivename)
    print('  created "{0}"'.format(fn))

    print("Removing temp directory")
    shutil.rmtree(archivename)

    print("\nFinished!  The zip file is:\n  {0}".format(fn))
    print("  (you may want to rename this)")
    if not all_ok:
        print("... but there were some warnings, see above")
