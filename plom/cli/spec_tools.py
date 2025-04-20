# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

from pathlib import Path

from plom.cli import with_messenger

from plom.plom_exceptions import PlomAuthenticationException, PlomConflict


@with_messenger
def upload_spec(toml: Path, *, msgr) -> bool:
    """Upload a new spec from a local toml file.

    Args:
        toml:  Path to a .toml file containing a valid assessment spec.
        msgr:  An active Messenger object.

    Returns:
        True if the server's specification was updated, otherwise False.
    """
    with open(toml, "rb") as f:
        tomlstring = f.read().decode("utf-8")

    try:
        msgr.new_server_upload_spec(tomlstring)
        check = msgr.new_server_get_spec()
    except (PlomAuthenticationException, PlomConflict, ValueError) as e:
        print(f"Upload failed with exception: {e}")
        return False

    print(f"Success: Server spec now addresses {check['name']}, {check['longName']}.")
    return True
