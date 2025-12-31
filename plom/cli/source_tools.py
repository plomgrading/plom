# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

from pathlib import Path

from plom.cli import with_messenger


@with_messenger
def upload_source(version: int, source_pdf: Path, *, msgr) -> bool:
    """Upload a new assessment source from a local PDF file.

    Args:
        version: integer number of source version
        source_pdf: Path to a PDF file containing a valid assessment source

    Keyword Args:
        msgr: An active Messenger object.

    Returns:
        True if the server's source was updated, otherwise False.
    """
    returndict = msgr.upload_source(version, source_pdf)

    returnversion = returndict["version"]
    if returnversion != version:
        print("Internal logic error. Mismatch between target and actual versions.")
        return False

    fsize = source_pdf.stat().st_size
    if fsize == 0:
        if not returndict["uploaded"]:
            print(f"Source version {version} deleted.")
            return True
        print(
            "Internal logic error: Empty upload should delete source, "
            "but that has not happened."
        )
        return False

    if returndict["uploaded"]:
        print(f"Source version {version} uploaded.")
        print(f"Uploaded hash is {returndict['hash']}.")
        return True

    print(
        "Internal logic error: Everything looked great until the end, "
        "but the upload has not been noted in the database."
    )
    return False


@with_messenger
def delete_source(version: int, *, msgr) -> bool:
    """Delete the specified assessment source.

    Args:
        version: integer number of source version

    Keyword Args:
        msgr: An active Messenger object.

    Returns:
        True if the server's source was updated, otherwise False.
    """
    msgr.delete_source(version)
    print(f"Source version {version} deleted.")
    return True
