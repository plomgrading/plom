# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from pathlib import Path
from typing import Any

from plom.cli import with_messenger


@with_messenger
def get_reassembled(papernum: int, *, msgr) -> dict[str, Any]:
    """Upload a bundle from a local pdf file."""
    return msgr.new_server_get_reassembled(papernum)
