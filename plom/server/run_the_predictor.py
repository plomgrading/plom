#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2021 Colin B. Macdonald

"""
Executable file frontend to the actual ID reader code.
"""

__copyright__ = "Copyright (C) 2018-20120 Andrew Rechnitzer and others"
__credits__ = ["Andrew Rechnitzer", "Dryden Wiebe", "Vala Vakilian"]
__license__ = "AGPLv3"

import csv
import json
import os
import sys

from .IDReader_RF.idReader import run_id_reader
from plom import specdir


if __name__ == "__main__":
    lock_file = sys.argv[1]

    if not os.path.isfile(lock_file):
        raise RuntimeError('Cannot acquire file "{}"'.format(lock_file))

    # Put student numbers in list
    print("Getting the classlist")
    student_IDs = []
    with open(specdir / "classlist.csv", newline="") as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=",")
        next(csv_reader, None)  # skip the header
        for row in csv_reader:
            student_IDs.append(row[0])

    with open(lock_file) as fh:
        fileDictAndRect = json.load(fh)

    print("Firing up the auto id reader.")
    prediction_pairs = run_id_reader(
        fileDictAndRect[0], fileDictAndRect[1], student_IDs
    )

    # now save the result
    with open(specdir / "predictionlist.csv", "w") as fh:
        fh.write("test, id\n")
        for test_number, student_ID in prediction_pairs:
            fh.write("{}, {}\n".format(test_number, student_ID))

    print("Results saved in predictionlist.csv")

    os.unlink(lock_file)
