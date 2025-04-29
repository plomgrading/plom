# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

from pathlib import Path
import traceback

from plom.cli import with_messenger

from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomDependencyConflict,
    PlomSeriousException,
    PlomVersionMismatchException,
)


@with_messenger
def upload_source(version, source_pdf: Path, *, msgr) -> bool:
    """Upload a new assessment source from a local PDF file.

    Args:
        version: integer number of source version
        source_pdf:  Path to a PDF file containing a valid assessment source
        msgr:  An active Messenger object.

    Returns:
        True if the server's source was updated, otherwise False.
    """
    with open(source_pdf, "rb") as f:
        try:
            returndict = msgr.new_server_upload_source(version, f)
        except (
            PlomAuthenticationException,
            PlomDependencyConflict,
            PlomVersionMismatchException,
            PlomSeriousException,
        ) as e:
            print(f"Upload failed with exception: {e}")
            traceback.print_exc()
            return False

    returnversion = returndict["version"]
    if returnversion != version:
        print("Massive catastrophe.")
        return False

    fsize = source_pdf.stat().st_size
    if fsize == 0:
        if not returndict["uploaded"]:
            print(f"Source version {version} deleted.")
            return True
        else:
            print(
                "ERROR: Empty upload should delete source, but that didn't happen. Why not?"
            )
            return False
    else:
        if returndict["uploaded"]:
            print(f"Source version {version} uploaded.")
            print(f"Uploaded hash is {returndict['hash']}.")
            return True

    return False
