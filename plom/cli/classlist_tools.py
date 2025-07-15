# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

import sys
from pathlib import Path

from plom.cli import with_messenger

from plom.plom_exceptions import PlomAuthenticationException, PlomConflict


@with_messenger
def delete_classlist(msgr) -> bool:
    """Remove all records from the classlist held on the server.

    Keyword Args:
        msgr:  An active Messenger object.

    Returns:
        True if the server's classlist was purged.
    """
    msgr.new_server_delete_classlist()
    print("OK, server's classlist is now empty.")
    return True


@with_messenger
def download_classlist(msgr) -> bool:
    """Echo all records from the server's classlist to stdout.

    Keyword Args:
        msgr:  An active Messenger object.

    Returns:
        True iff the server's classlist was emitted.
    """
    success = True
    csvstream = msgr.new_server_download_classlist()
    for chunk in csvstream:
        sys.stdout.buffer.write(chunk)
    return success


@with_messenger
def upload_classlist(csvname: Path, *, msgr) -> bool:
    """Take lines from the given CSV file and add them to the server's classlist.

    Enforce uniqueness of student ID's and test numbers in the upload:
    Any duplication at all will cancel the entire operation.

    Args:
        csvname: The path to a valid classlist CSV file.

    Keyword Args:
        msgr: An active Messenger object.

    Returns:
        True iff the server's classlist now includes all uploaded records.
    """
    try:
        success, werr = msgr.new_server_upload_classlist(csvname)
    except (PlomAuthenticationException, PlomConflict) as e:
        success = False
        werr = []
        print(f"Upload failed with exception: {e}")

    if success:
        if len(werr) > 0:
            print(f"Upload succeeded, with {len(werr)} note(s) shown below.")
            for D in werr:
                print(f"  {D.get('warn_or_err', '  *')}: {D['werr_text']}")
        return True

    print("Upload rejected. No changes made to server's classlist. Details follow.")
    for D in werr:
        print(f"  {D.get('warn_or_err', '  *')}: {D['werr_text']}")
    return False
