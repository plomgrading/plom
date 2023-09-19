#!/usr/bin/env python3

# List the assignments for the user with a given API key.

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Philip D. Loewen

from canvasapi import Canvas
import os
import sys
from pathlib import Path
import csv

api_key = os.environ.get("CANVAS_API_KEY", None)

if api_key is None:
    homedir = os.environ["HOME"]
    # print("Home directory is {:s}.".format(homedir))
    secretsfile = Path(f"{homedir}/.secrets/canvas-api-key")
    # print(f"secretsfile is {secretsfile}.")
    if os.path.exists(secretsfile) and os.access(secretsfile, os.R_OK):
        with open(secretsfile, "r") as f:
            api_key = f.read()
        print(f"Retrieved CANVAS_API_KEY from {secretsfile}.")

if api_key is None:
    print("This script requires a Canvas API key to be provided")
    print("in the environment variable CANVAS_API_KEY.")
    print("A fallback search in the file {} failed.".format(secretsfile))
    print("That variable remains unset, so execution cannot continue.")
    sys.exit(1)

api_url = "https://canvas.ubc.ca"
canvas = Canvas(api_url, api_key)
me = canvas.get_current_user()
my_courses = me.get_courses()

print(f"\nThe given key identifies {me.name}, ", end="")
print(f"user number {me.id}.\n")

print(f"User {me.id} has TeacherEnrollment role in the following courses [CSV]:\n")
print(80 * "=")

# Canvas returns many course objects, some with unexpected characteristics.
# Ignore those in what follows. Build a dict of apparently-relevant ones.

cnum2title = {}  # Prefix 'c' indicates 'course number to [course] title'
for c in my_courses:
    if hasattr(c, "course_code") and hasattr(c, "enrollments"):
        for d in c.enrollments:
            # Each d is a dict of roles, etc.
            # If one shows me in the Teacher role, print it and
            # ignore the rest.
            if d["user_id"] == me.id and d["role"] == "TeacherEnrollment":
                cnum2title[int(c.id)] = c.name

stdout_ = sys.stdout
csvwriter = csv.writer(stdout_, quoting=csv.QUOTE_NONNUMERIC)
csvwriter.writerow(
    ["Course ID", "Assignment ID", "Point Value", "Assignment Title", "Course Title"]
)
for cnum, ctitle in sorted(cnum2title.items(), key=lambda kv: kv[1]):
    # print(f"DEBUG: Thinking about cnum {cnum} and ctitle {ctitle}")

    anum2title = {}  # Prefix 'a' indicates 'assignment number to [assignment] title'
    anum2value = {}  # Prefix 'a' indicates 'assignment number to [assignment] value'

    aa = [
        hwobject
        for hwobject in canvas.get_course(cnum).get_assignments()
        if hasattr(hwobject, "name")
    ]
    for ii, aa in enumerate(aa):
        anum2title[aa.id] = aa.name
        anum2value[aa.id] = aa.points_possible
    # print(f"Found {len(anum2title)} named assignments.")

    # print(aa)
    for anum, atitle in sorted(anum2title.items(), key=lambda kv: kv[1]):
        # print(f"    DEBUG: Thinking about anum {anum} and atitle {atitle}")
        value = anum2value[anum]
        csvwriter.writerow([cnum, anum, value, atitle, ctitle])

del canvas
sys.exit(0)
