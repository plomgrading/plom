# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from csv import DictWriter
from io import StringIO
from typing import Any

from plom.cli import with_messenger


@with_messenger
def get_marks_as_csv_string(*, papernum: int | None = None, msgr) -> str:
    """Get exam paper marks as a csv formatted string.

    Keyword Args:
        papernum: the paper number to retrieve exam paper marks. If
            unspecified, exam paper marks will be retrieved for all papers.
        msgr: a valid PlomAdminMessenger instance.

    Returns:
        A string containing the paper marks formatted as a csv.
    """
    papers_marks_list = msgr.new_server_get_paper_marks()

    # TODO: remove this feature?
    # if we don't want to remove it, this should be a query param for the API
    # which can then return the actual error.
    if papernum is not None:
        for marks_dict in papers_marks_list:
            if marks_dict["PaperNumber"] == papernum:
                papers_marks_list = [marks_dict]
                break
        if not len(papers_marks_list) == 1:
            raise ValueError(f"Paper {papernum} doesn't exist or hasn't been ID'd.")

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
