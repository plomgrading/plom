# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from typing import Any

from plom.cli import with_messenger


@with_messenger
def id_paper(
    papernum: int, student_id: str, student_name: str, *, msgr
) -> dict[str, Any]:
    """Directly identify a particular paper as belonging to a particular student id."""
    return msgr.beta_id_paper(papernum, student_id, student_name)


@with_messenger
def un_id_paper(papernum: int, *, msgr) -> dict[str, Any]:
    """Unidentify a particular paper."""
    return msgr.beta_un_id_paper(papernum)
