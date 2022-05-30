# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2022 Colin B. Macdonald

import json

from plom.finish import with_finish_messenger
from plom.finish import RubricListFilename, TestRubricMatrixFilename


@with_finish_messenger
def download_rubric_files(*, msgr):
    """Download two files with information about rubrics.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
    """
    counts = msgr.RgetRubricCounts()
    tr_matrix = msgr.RgetTestRubricMatrix()

    # counts is a dict indexed by key - turn it into a list
    # this makes it compatible with plom-create rubric upload
    rubric_list = [Y for X, Y in counts.items()]

    with open(RubricListFilename, "w") as fh:
        json.dump(rubric_list, fh, indent="  ")

    with open(TestRubricMatrixFilename, "w") as fh:
        json.dump(tr_matrix, fh)
