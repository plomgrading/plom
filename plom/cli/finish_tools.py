# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from typing import Any
from tempfile import NamedTemporaryFile

from plom.cli import with_messenger


@with_messenger
def get_reassembled(papernum: int, *, msgr) -> dict[str, Any]:
    """Get a paper in its marked state."""
    with NamedTemporaryFile("wb+") as memfile:
        msgr.new_server_get_reassembled(papernum, memfile)
        with open(memfile.name, "wb") as permanentfile:
            memfile_contents = memfile.read()
            permanentfile.write(memfile_contents)
            info_dict = {
                "filename": memfile.name,
                "content-length": len(memfile_contents),
            }

    return info_dict


@with_messenger
def get_unmarked(papernum: int, *, msgr) -> dict[str, Any]:
    """Get a paper in its unmarked state."""
    with NamedTemporaryFile("wb+") as memfile:
        msgr.new_server_get_unmarked(papernum, memfile)
        with open(memfile.name, "wb") as permanentfile:
            memfile_contents = memfile.read()
            permanentfile.write(memfile_contents)
            info_dict = {
                "filename": memfile.name,
                "content-length": len(memfile_contents),
            }

    return info_dict
