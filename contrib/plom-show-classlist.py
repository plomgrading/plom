#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Forest Kobayashi
# Copyright (C) 2021-2023 Colin B. Macdonald
# Copyright (C) 2022 Nicholas J H Lai
# Copyright (C) 2023 Philip Loewen

"""
Connect to a running Plom server and retrieve its classlist,
communicating exclusively through a ManagerMessenger.

Environment variables PLOM_SERVER and PLOM_MANAGER_PASSWORD
are essential. Perhaps PLOM_NO_SSL_VERIFY must also have a value.

This is for learning and experimentation.
It does not change anything on the server.

The classlist that comes back has a field named paper_number that 
is apparently *not* updated when an ID is assigned to the student
named on the list. So that field cannot be trusted at later stages 
of any operation.

Instead, the ManagerMessenger can get the paper_number from the
database ... if some condition not known to me is in force.
Experimentation suggests that you get an integer if the student
of interest has a paper and None if they don't.

This version by Philip D Loewen, 2023-09-18; original by others.
"""

import os
import sys
from plom.create import start_messenger

if not hasattr(os, "PLOM_MANAGER_PASSWORD") or not hasattr(os, "PLOM_SERVER"):
    print("At least one required environment variable is missing. Quitting.")
    sys.exit(1)

manager_pwd = os.environ["PLOM_MANAGER_PASSWORD"]
server = os.environ["PLOM_SERVER"]

try:
    mm = start_messenger(server, manager_pwd)

    classlist = mm.IDrequestClasslist()
    sid2name = {}  # Dict will return student's name, a string
    sid2preid = {}  # Dict will return suggested preid from classlist
    sid2paper = {}  # Dict will return actual paper number according to database
    for k in range(len(classlist)):
        sid = classlist[k]["id"]
        sid2name[sid] = classlist[k]["name"]
        sid2preid[sid] = int(classlist[k]["paper_number"])

        r = mm.sid_to_paper_number(sid)
        if not r[0]:
            # print(f"  Test lookup failed for sid = {sid}")
            sid2paper[sid] = None
        else:
            testnum = r[1]
            # print(f"  Test number {testnum} found for sid = {sid}")
            sid2paper[sid] = testnum
finally:
    mm.closeUser()
    mm.stop()

print("\nServer API includes this info:\n")
# Slick Python method delivers the class list alphabetized by surname
for sid, name in sorted(sid2name.items(), key=lambda kv: kv[1]):
    print(
        f"sid={sid}: {sid2name[sid]}, with preid={sid2preid[sid]} and actual test={sid2paper[sid]}"
    )
