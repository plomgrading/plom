# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Andrew Rechnitzer

import json
from plom.finish import start_messenger


def main(server=None, password=None):
    msgr = start_messenger(server, password)
    try:
        audit = msgr.RgetFileAudit()
    finally:
        msgr.closeUser()
        msgr.stop()

    with open("audit.json", "w+") as fh:
        json.dump(audit, fh, indent="  ")
    print("Wrote file audit to 'audit.json'")


if __name__ == "__main__":
    main()
