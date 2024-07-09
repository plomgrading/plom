#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021, 2024 Colin B. Macdonald
# Copyright (C) 2020 Jenny Li

"""Update the mappings to for human-readable room, time, and emerg. links.

*** IMPORTANT STUFF TO CHANGE
 * See Room names below
 * backup url (make new one)

New/modified columns:
    test_room_human
    backup_submit_url
    test_time
"""

from pathlib import Path
import pandas as pd


where_csv = Path(".")
in_csv = where_csv / "Canvas_classlist_042_urls.csv"
out_csv = where_csv / "Canvas_classlist_043_ready.csv"

df = pd.read_csv(in_csv, index_col=False, dtype="object")

# Make a new one for your test
link = "https://nextcloud.example.com/index.php/s/UPDATE_ME"

# Update these mappings
room_name_to_human = {
    "quiz1": "Quiz 1",
    "cfa": "With the CfA",
    "evening": "Quiz 1 Evening",
}
room_name_to_backup_link = {
    "quiz1": link,
    "cfa": link,
    "evening": link,
}
room_name_to_time = {
    "quiz1": "2:00pm",
    "cfa": "2:00pm",
    "evening": "9:00pm",
}

print("The mappings are:")
print("  human-readable room names: {}".format(room_name_to_human))
print("  emerg backup submit links: {}".format(room_name_to_backup_link))
print("  times: {}".format(room_name_to_time))
print("Have you updated those?  Made new link(s)?")
input("Press enter to continue, ctrl-C to stop ")

df["test_room_human"] = df["test_room"].map(room_name_to_human)
df["test_backup_submit_url"] = df["test_room"].map(room_name_to_backup_link)
df["test_time"] = df["test_room"].map(room_name_to_time)


def assert_it_worked(r):
    if (
        pd.isnull(r["test_room_human"])
        or pd.isnull(r["test_backup_submit_url"])
        or pd.isnull(r["test_time"])
    ):
        print("problem row:")
        print(r)
        raise ValueError("Expect non-null entry was not!  Missing student somewhere?")


df.apply(assert_it_worked, axis=1)

df.to_csv(out_csv, index=False)
