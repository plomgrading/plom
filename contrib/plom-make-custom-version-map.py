#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Colin B. Macdonald

"""Make a custom version map.

This can be used a paper production time like this:

plom-create make-db --from-file custom_question_version_map.csv

This example is for multiple sittings.  Versions 1, 2, and 3
are interleaved randomly as usual for the first 200 papers.
Then versions 4, 5 and 6 are interleaved for papers 200 to 400.
"""

import random

from plom.version_maps import version_map_to_csv


if __name__ == "__main__":
    num_questions = 5

    qvmap = {}
    for n in range(1, 199 + 1):
        # randomly select between 1, 2, and 3
        row = {}
        for q in range(1, num_questions + 1):
            row[q] = random.choice([1, 2, 3])
        qvmap[n] = row
    for n in range(200, 400 + 1):
        # randomly select between 4, 5, and 6
        row = {}
        for q in range(1, num_questions + 1):
            row[q] = random.choice([4, 5, 6])
        qvmap[n] = row
    version_map_to_csv(qvmap, "custom_question_version_map.csv")
