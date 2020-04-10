#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

import json
import os
import sys

lockFile = sys.argv[1]

if not os.path.isfile(lockFile):
    exit(1)

with open(lockFile) as fh:
    fileDictAndRect = json.load(fh)
    from .idReader import runIDReader

    runIDReader(fileDictAndRect[0], fileDictAndRect[1])

os.unlink(lockFile)
