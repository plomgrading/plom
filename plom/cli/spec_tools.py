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
        (True)  Spec got updated
        (False) Opposite of true
    """
    rc = False  # Nothing achieved *yet*
    try:
        filepointer = open(toml, "rb")
    except FileNotFoundError:
        print(f"Error: File '{toml}' not found. Assessment spec unchanged.")
        return rc
    except PermissionError:
        print(f"Error: Cannot read file '{toml}'. Assessment spec unchanged.")
        return rc
    except Exception:
        print("Something went wrong. Assessment spec unchanged.")
        return rc

    tomlbytes = filepointer.read()
    tomlstring = tomlbytes.decode("utf-8")

    try:
        msgr.new_server_upload_spec(tomlstring)
        check = msgr.new_server_get_spec()
        print(
            f"Success: Server spec now addresses {check['name']}, {check['longName']}."
        )
        rc = True
    except Exception as e:
        print(f"Upload failed with exception: {e}")
        return rc

    return rc
