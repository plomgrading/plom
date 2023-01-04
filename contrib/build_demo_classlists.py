#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer

"""Simple script to build a list of random first/last names starting with 'Ex'.

Also constructs random 8 digit student numbers which do not clash with those in the existing demoClassList.csv file.

Requires the names_dataset which is (essentially) a big dump of names from facebook.
"""


import csv
import json
from names_dataset import NameDataset
from pathlib import Path
import random

sid = {}
dcl = Path("../plom/demoClassList.csv")
with open(dcl) as fh:
    red = csv.DictReader(fh)
    for row in red:
        sid[int(row["id"])] = row["name"]

nd = NameDataset()

x_first = []
x_last = []

for person in nd.first_names:
    if person[:2] == "Ex" and " " not in person:
        x_first.append(person)

for person in nd.last_names:
    if person[:2] == "Ex" and " " not in person:
        x_last.append(person)

N = 60
id_and_name = []
for (a, b) in zip(random.choices(x_first, k=N), random.choices(x_last, k=N)):
    while True:
        id = random.randint(10**7, 10**8)
        if id not in sid:
            break
    id_and_name.append((f"{id}", f"{b}, {a}"))

print(json.dumps(id_and_name))
