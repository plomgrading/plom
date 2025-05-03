# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

# import sys
from pathlib import Path

from plom.cli import with_messenger

from plom.plom_exceptions import PlomAuthenticationException, PlomConflict


@with_messenger
def upload_classlist(csvname: Path, *, msgr) -> bool:
    """Take lines from the given CSV file and add them to the server's classlist.

    Reject the whole file if some ID's from the given file are already present
    on the server.

    Args:
        csvname: The path to a valid classlist CSV file.

    Keyword Args:
        msgr:  An active Messenger object.
    """
    print(f"In plom-cli, planning to process file {csvname}.")

    try:
        retval = msgr.new_server_upload_classlist(csvname)
    except (PlomAuthenticationException, PlomConflict, ValueError) as e:
        print(f"Upload failed with exception: {e}")
        return False

    print("In plom-cli, here is the return value.")
    print(retval)

    return True
