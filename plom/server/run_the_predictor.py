#!/bin/env -S python3 -u
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2023 Colin B. Macdonald

"""
Executable file frontend to the actual ID reader code.
"""

__copyright__ = "Copyright (C) 2018-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import json
from pathlib import Path
import sys

from plom.idreader.model_utils import download_or_train_model
from plom.idreader.predictStudentID import compute_probabilities

from plom import specdir


if __name__ == "__main__":
    lock_file = Path(sys.argv[1])

    if not lock_file.exists():
        raise RuntimeError(f'Cannot acquire file "{lock_file}"')

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

    lock_file.unlink()

    print("")
    print("**** Auto id reader has finished ****")
