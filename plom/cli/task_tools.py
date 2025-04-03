# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from typing import Any

from plom.cli import with_messenger


@with_messenger
def reset_task(papernum: int, question_idx: int, *, msgr) -> dict[str, Any]:
    """Upload a bundle from a local pdf file."""
    return msgr.reset_task(papernum, question_idx)
