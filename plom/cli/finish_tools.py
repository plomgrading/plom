# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from csv import DictWriter
from io import StringIO
from typing import Any

from plom.cli import with_messenger


@with_messenger
def get_marks_as_csv_string(*, msgr) -> str:
    """Get exam paper marks as a csv formatted string.

    Keyword Args:
        msgr: a valid PlomAdminMessenger instance.

    Returns:
        A string containing the paper marks formatted as a csv.
    """
    papers_marks_list = msgr.new_server_get_paper_marks()

    with StringIO() as stringbuffer:
        writer = DictWriter(stringbuffer, papers_marks_list[0].keys())

        writer.writeheader()
        writer.writerows(papers_marks_list)
        csv_string = stringbuffer.getvalue()

    return csv_string


@with_messenger
def get_reassembled(papernum: int, *, msgr) -> dict[str, Any]:
    """Get a paper in its marked state."""
    return msgr.new_server_get_reassembled(papernum)


@with_messenger
def get_unmarked(papernum: int, *, msgr) -> dict[str, Any]:
    """Get a paper in its unmarked state."""
    return msgr.new_server_get_unmarked(papernum)
