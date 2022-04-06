#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2022 Colin B. Macdonald

"""
Executable file frontend to the actual ID reader code.
"""

__copyright__ = "Copyright (C) 2018-2022 Andrew Rechnitzer and others"
__credits__ = ["Andrew Rechnitzer", "Dryden Wiebe", "Vala Vakilian"]
__license__ = "AGPLv3"

import json
import os
import sys

from plom.idreader.model_utils import download_or_train_model
from plom.idreader.predictStudentID import compute_probabilities

from plom import specdir


if __name__ == "__main__":
    lock_file = sys.argv[1]

    if not os.path.isfile(lock_file):
        raise RuntimeError('Cannot acquire file "{}"'.format(lock_file))

    with open(lock_file) as fh:
        files, info = json.load(fh)

    print("Firing up the auto id reader.")

    print("Ensuring we have the model: download if not, or train if cannot download...")
    download_or_train_model()

    print("Computing probabilities")
    # Number of digits in the student ID.
    student_number_length = 8
    probabilities = compute_probabilities(
        files, info["crop_top"], info["crop_bottom"], student_number_length
    )
    # numpy does not jsonify: maybe change compute_probabilities to return arrays?
    probabilities = {k: [x.tolist() for x in v] for k, v in probabilities.items()}
    with open(specdir / "id_prob_heatmaps.json", "w") as fh:
        json.dump(probabilities, fh, indent="  ")

    os.unlink(lock_file)

    print("Auto id reader has finished")
