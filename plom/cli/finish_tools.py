# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from csv import DictWriter
from io import StringIO
from typing import Any
from tempfile import NamedTemporaryFile

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
    papers_marks_dict = msgr.new_server_get_paper_marks()
    if papernum is not None:
        papers_marks_dict = {papernum: papers_marks_dict[str(papernum)]}
    papers_marks_list = [marks_dict for marks_dict in papers_marks_dict.values()]

    # TODO: API doesn't return a consistent set of fields in each dict
    dict_keys = []
    for marks_dict in papers_marks_list:
        for key in marks_dict.keys():
            if key not in dict_keys:
                dict_keys.append(key)

    with StringIO() as stringbuffer:
        writer = DictWriter(stringbuffer, dict_keys)

        writer.writeheader()
        writer.writerows(papers_marks_list)
        csv_string = stringbuffer.getvalue()

    return csv_string


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
    return msgr.new_server_get_unmarked(papernum)
