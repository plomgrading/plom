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

import json
import os
import sys

# Older not-recently tested TensorFlow model
# from .IDReader_TF.idReader import run_id_reader
from .IDReader_RF.idReader import run_id_reader


if __name__ == "__main__":
    lock_file = sys.argv[1]

    if not os.path.isfile(lock_file):
        raise RuntimeError('Cannot acquire file "{}"'.format(lock_file))

    with open(lock_file) as fh:
        fileDictAndRect = json.load(fh)
        run_id_reader(fileDictAndRect[0], fileDictAndRect[1])

    os.unlink(lock_file)
