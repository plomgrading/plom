# -*- coding: utf-8 -*-

"""Check which students have submitted what in the submittedHomework directory"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
import glob


def extractIDQ(fileName):
    """Expecting filename of the form blah.SID.Q.pdf - return SID and Q"""
    splut = fileName.split(".")
    return (splut[-3], int(splut[-2]))


def main():
    whoDidWhat = defaultdict(list)
    for fn in glob.glob("submittedHomework/*.pdf"):
        sid, q = extractIDQ(fn)
        whoDidWhat[sid].append(q)
    for sid in whoDidWhat:
        print("#{} submitted {}".format(sid, whoDidWhat[sid]))


if __name__ == "__main__":
    main()
