# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

from pathlib import Path

from plom.cli import with_messenger


@with_messenger
def upload_spec(toml: Path, *, msgr) -> bool:
    """Upload a new spec from a local toml file.

    Args:
        toml:  Path to a .toml file containing a valid assessment spec.
        msgr:  An active Messenger object.

    Returns:
        (True): Always
    """
    filepointer = open(toml, "rb")
    tomlbytes = filepointer.read()
    tomlstring = tomlbytes.decode("utf-8")

    msgr.new_server_upload_spec(tomlstring)

    return True  # Could do something fancier after looking at return value above
