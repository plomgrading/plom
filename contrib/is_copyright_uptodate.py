#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Colin B. Macdonald

"""Output the names of files given as args that are not copyright in a given year.

Gives non-zero exit code if there were any that need updates.

Also, snitches on files without apparent copyright headers, although
in some cases, maybe they have to be like that!
"""

import re
import sys
from datetime import datetime

year = datetime.utcnow().year
p = re.compile(f".*Copyright.*{year}.*")
p2 = re.compile(".*Copyright.*")

if __name__ == "__main__":
    at_least_one = False
    files = set(sys.argv[1:])
    print(f"Checking copyright headers for {year} in {len(files)} files...")
    for f in files:
        try:
            with open(f, "r") as fh:
                data = fh.read().replace("\n", "")
        except UnicodeDecodeError:
            print(f"    Skipping binary (?) file: {f}")
            continue
        except FileNotFoundError:
            print(f"    Skipping deleted (?) file: {f}")
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
