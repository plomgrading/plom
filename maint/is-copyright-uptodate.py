#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov

"""Output the names of files given as args that are not copyright in a given year.

Gives non-zero exit code if there were any that need updates.

Also, snitches on files without apparent copyright headers, although
in some cases, maybe they have to be like that!
"""

import re
from pathlib import Path
import sys
from datetime import datetime, timezone

year = datetime.now(timezone.utc).year
p = re.compile(f".*Copyright.*{year}.*")
p2 = re.compile(".*Copyright.*")
re_alt = re.compile(".*creativecommons.org/(licenses|publicdomain)/.*")

# Some files don't have copyright info: can consider whether this is ok,
# but for now we can avoid hearing about them by listing globs:
ok_no_copyright = [
    "CHANGELOG*",
    "CONTRIBUTORS*",
    "*README.md",
    "*README.txt",
    "*/ui_files/ui_*.py",
    ".mailmap",
    "*/cl_*.csv",
    "*/demo_assessment_*.csv",
    "*/demoClassList.csv",
    "*papers_to_rooms.csv",
    "plom_server/static/*.svg",
    "testTemplates/idBox*.eps",
    "testTemplates/idBox*.svg",
    "*/migrations/00??_initial.py",
]

if __name__ == "__main__":
    at_least_one = False
    files = set(sys.argv[1:])
    print(f"Checking copyright headers for {year} in {len(files)} files...")
    for f in files:
        f = Path(f)
        if any(f.match(x) for x in ok_no_copyright):
            print(f"    matches the allow list, skip: {f}")
            continue
        try:
            with open(f, "r") as fh:
                data = fh.read().replace("\n", "")
        except UnicodeDecodeError:
            print(f"    Skipping binary (?) file: {f}")
            continue
        except FileNotFoundError:
            print(f"    Skipping deleted (?) file: {f}")
            continue
        if re_alt.match(data):
            print(f"    File has creativecommons licence url: {f}")
            continue
        if not p2.match(data):
            print(f"[!] File without copyright header: {f}")
            # TODO: or leave as False to just skip these
            at_least_one = True
            continue
        if not p.match(data):
            at_least_one = True
            print(f"[w] Needs copyright header update: {f}")
    if at_least_one:
        print("At least one file needs updated, see list above")
        sys.exit(1)
    print("No files need updates")
    sys.exit(0)
