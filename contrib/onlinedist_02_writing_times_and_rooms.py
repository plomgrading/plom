#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021, 2023-2024 Colin B. Macdonald
# Copyright (C) 2021 Jenny Li

"""We may have students writing in different rooms at different times, create columns for room.

Input should be a Canvas export with non-students removed:
No "Student, test" etc, everyone must have student numbers.  A previous
"01" script should make this for you, or you can do it manually.

You will likely need to modify this depending on how students are divided
into rooms.

New columns:
    "test_room": a short machine-readable name for a room, appropriate
        for part of a url or dict key.  E.g., "quiz1roomA".
    "test_room_human": a human-readable name for a Room, either a physical
        room or name of a video conference room.  For now, we leave this
        blank and use a dict later to fill it from above.
    "test_time": a human-readable time to write, e.g., "Monday 9pm".
        For now, we leave this blank and replace it later using a dict.
    "test_notes": a blank column for other notes to transmit to students.
"""

from pathlib import Path
from math import nan

import pandas as pd


where_csv = Path(".")
canvas_csv = where_csv / "Canvas_classlist_01_cleaned.csv"
out_csv = where_csv / "Canvas_classlist_02_with_rooms.csv"
manual_csv = where_csv / "Canvas_classlist_02_with_rooms_edited.csv"

df = pd.read_csv(canvas_csv, dtype="object")

print("What this should do depends on your situation: have you modified the script?")
input("Press enter to continue or ctrl-C to stop ")

# E.g., Room name is "Quiz 1 - 203" with 203 varying by Lecture (Section)
# df["test_room"] = "quiz1-" + df["Lecture"]

# E.g., Random rooms
# RoomList = ["roomA", "roomB", "roomC", "roomD"]
# df["test_room"] = df.apply(lambda r: random.choice(RoomList), axis=1)

# Idea: use Canvas API to pull the times from a Canvas Assignment where
# someone has already customized the times.

# E.g., everyone in same room
df["test_room"] = "quiz1"
# except a few:
cfa = pd.read_csv("cfa.csv", dtype="object")
evening = pd.read_csv("evening.csv", dtype="object")
for mod in (cfa, evening):
    # dict of ID -> test_room
    mymap = mod.set_index("ID")["test_room"].to_dict()

    def f(row):
        r = mymap.get(row["ID"], None)
        if r:
            return r
        else:
            return row["test_room"]

    df["test_room"] = df.apply(f, axis=1)
# double check right number of unique rooms
expect_distinct_rooms = 4
assert len(df["test_room"].unique()) == expect_distinct_rooms


# to be filled-in later
df["test_room_human"] = nan
df["test_time"] = nan
# to be filled-in manually if needed for personalized messages
df["test_notes"] = nan

print('If you need, you can manually edit the "{}" spreadsheet'.format(out_csv))
print("for example, to modify some students Rooms, or add Notes.")
print('When finished, save the result as:\n  "{}"'.format(manual_csv))

df.to_csv(out_csv, index=False)
