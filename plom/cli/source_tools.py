# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

from pathlib import Path

from plom.cli import with_messenger

from plom.plom_exceptions import PlomAuthenticationException, PlomConflict


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
            r = msgr.post_auth(f"/api/v0/source/{version:d}", files={"source_pdf": f})
        except (
            PlomAuthenticationException,
            PlomConflict,
            ValueError,
        ) as e:  # TODO - check these
            print(f"Upload failed with exception: {e}")
            return False

    #########
    # Handle errors here temporarily -- ideas will move to messenger on next iteration
    if r.status_code != 200:
        print(f"Something went wrong. HTTP {r.status_code:d}, with reason below:")
        print(r.reason)
        return False
    #########

    returndict = r.json()
    returnversion = returndict["version"]
    if returnversion != version:
        print("Massive catastrophe.")
        return False

    fsize = source_pdf.stat().st_size
    if fsize == 0:
        if not returndict["uploaded"]:
            print(f"Source version {version} successfully deleted.")
            return True
        else:
            print(
                "ERROR: Empty upload should delete source, but that didn't happen. Why not?"
            )
            return False
    else:
        if returndict["uploaded"]:
            print(f"Source version {version} successfully uploaded.")
            print(f"Uploaded hash is {returndict['hash']}.")
            return True
