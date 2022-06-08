# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer
# Copyright (C) 2022 Colin B. Macdonald

import json

from plom.finish import with_finish_messenger


@with_finish_messenger
def audit(*, msgr):
    audit = {}
    audit["tests"] = msgr.getFilesInAllTests()
    audit["unknowns"] = msgr.getUnknownPages()
    audit["discards"] = msgr.getDiscardedPages()
    audit["dangling"] = msgr.getDanglingPages()
    audit["collisions"] = msgr.getCollidingPageNames()

    with open("audit.json", "w+") as fh:
        json.dump(audit, fh, indent="  ")
    print("Wrote file audit to 'audit.json'")
