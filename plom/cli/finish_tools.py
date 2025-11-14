# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from csv import DictWriter
from io import StringIO
from os import mkdir, chdir, getcwd
from typing import Any

from plom.cli import with_messenger
from plom.plom_exceptions import PlomException

from tqdm import tqdm


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
def get_reassembled(papernum: int, *, msgr, verbose: bool = False) -> dict[str, Any]:
    """Get a paper in its marked state."""
    return msgr.new_server_get_reassembled(papernum, verbose=verbose)


@with_messenger
def get_unmarked(papernum: int, *, msgr, verbose: bool = False) -> dict[str, Any]:
    """Get a paper in its unmarked state."""
    return msgr.new_server_get_unmarked(papernum, verbose=verbose)


@with_messenger
def get_all_reassembled(
    *, dirname: str = "reassembled", msgr, verbose: bool = False
) -> dict[str, Any]:
    """Get all papers in their marked states.

    Raises:
        OSError: directory already exists or cannot be written to.
    """
    pqvmap_dict = msgr.new_server_get_pqvmap()
    previous_cwd = getcwd()
    paper_count = 0
    content_length = 0

    mkdir(dirname)  # this raises an error if it dirname/ already exists
    chdir(dirname)
    for papernum_string in tqdm(pqvmap_dict.keys()):
        papernum = int(papernum_string)
        try:
            r = msgr.new_server_get_reassembled(papernum, verbose=verbose)
            paper_count += 1
            content_length += r["content-length"]

        except PlomException as err:
            print(err)
    chdir(previous_cwd)

    information = {
        "dirname": dirname,
        "num-papers": paper_count,
        "content-length": content_length,
    }
    return information


@with_messenger
def get_all_unmarked(
    *, dirname: str = "unmarked", msgr, verbose: bool = False
) -> dict[str, Any]:
    """Get all papers in their unmarked states.

    Raises:
        OSError: directory already exists or cannot be written to.
    """
    pqvmap_dict = msgr.new_server_get_pqvmap()
    previous_cwd = getcwd()
    paper_count = 0
    content_length = 0

    mkdir(dirname)  # this raises an error if dirname/ already exists
    chdir(dirname)
    for papernum_string in tqdm(pqvmap_dict.keys()):
        papernum = int(papernum_string)
        try:
            r = msgr.new_server_get_unmarked(papernum, verbose=verbose)
            paper_count += 1
            content_length += r["content-length"]

        except PlomException as err:
            print(err)
    chdir(previous_cwd)

    information = {
        "dirname": dirname,
        "num-papers": paper_count,
        "content-length": content_length,
    }
    return information
