#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from specParser import SpecParser

spec = SpecParser().spec

if os.path.isfile("plom.db"):
    print("A database file is present - good - you are ready to continue.")
else:
    print('There is no database file "plom.db" -  did you run 003?')
    exit(1)


print("There are two options for building PDFs - with or without names pre-filled.")
print("\t- the 004a script builds PDFs **without** names.")
print(
    "\t - the 004b script builds PDFs **with** names. The names are read from the classlist in order."
)
print(
    "Your test specification says you want to build {} papers of which {} should be named.".format(
        spec["numberToProduce"], spec["numberToName"]
    )
)
if spec["numberToName"] > 0:
    print("Based on your spec it looks like you should run 004b")
else:
    print("Based on your spec it looks like you should run 004a")
