# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from typing import Any

from plom.cli import with_messenger


@with_messenger
def get_reassembled(papernum: int, *, msgr) -> dict[str, Any]:
    """Get a paper in its marked state."""
    return msgr.new_server_get_reassembled(papernum)


@with_messenger
def get_unmarked(papernum: int, *, msgr) -> dict[str, Any]:
    """Get a paper in its unmarked state."""
    return msgr.new_server_get_unmarked(papernum)
