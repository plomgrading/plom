#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

"""Make a custom version map.

This can be used a paper production time like this:

plom-create make-db --from-file custom_question_version_map.csv

This example is for multiple sittings.  The instructor wanted
even/odd paper numbers to alternate between versions 1 and 2
for papers 1 to 199 (for the first sitting).  Then alternate
between versions 3 and 4 for papers 200-500 (the second sitting).
"""

from math import remainder

from plom.create.version_map_utils import _version_map_to_csv


if __name__ == "__main__":
    num_questions = 5

    qvmap = {}
    for n in range(1, 200):
        if remainder(n, 2) == 0:
            row = {q: 2 for q in range(1, num_questions + 1)}
        else:
            row = {q: 1 for q in range(1, num_questions + 1)}
        qvmap[n] = row
    for n in range(200, 501):
        if remainder(n, 2) == 0:
            row = {q: 4 for q in range(1, num_questions + 1)}
        else:
            row = {q: 3 for q in range(1, num_questions + 1)}
        qvmap[n] = row
    print(qvmap)
    _version_map_to_csv(qvmap, "custom_question_version_map.csv")
