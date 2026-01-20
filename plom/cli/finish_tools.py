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
def get_marks_as_csv_string(*, msgr) -> str:
    """Get exam paper marks as a csv formatted string.

    Keyword Args:
        msgr: a valid PlomAdminMessenger instance.

    Returns:
        A string containing the paper marks formatted as a csv.
    """
    papers_marks_list = msgr.get_paper_marks()

    with StringIO() as stringbuffer:
        writer = DictWriter(stringbuffer, papers_marks_list[0].keys())

        writer.writeheader()
        writer.writerows(papers_marks_list)
        csv_string = stringbuffer.getvalue()

    return csv_string


@with_messenger
def get_reassembled(papernum: int, *, msgr, verbose: bool = False) -> dict[str, Any]:
    """Get a paper in its marked state."""
    return msgr.get_reassembled(papernum, verbose=verbose)


@with_messenger
def get_unmarked(papernum: int, *, msgr, verbose: bool = False) -> dict[str, Any]:
    """Get a paper in its unmarked state."""
    return msgr.get_unmarked(papernum, verbose=verbose)


@with_messenger
def get_report(papernum: int, *, msgr, verbose: bool = False) -> dict[str, Any]:
    """Get a student report for a given paper."""
    return msgr.get_report(papernum, verbose=verbose)


@with_messenger
def get_all_reports(
    *, dirname: str = "reports", msgr, verbose: bool = False
) -> dict[str, Any]:
    """Get student reports for all papers."""
    pqvmap_dict = msgr.get_pqvmap()
    papernum_list = [int(papernum) for papernum in pqvmap_dict.keys()]

    return _get_all_helper(
        papernum_list,
        msgr.get_report,
        dirname=dirname,
        verbose=verbose,
    )


@with_messenger
def get_solution(papernum: int, *, msgr, verbose: bool = False) -> dict[str, Any]:
    """Get a solution set for a given paper."""
    return msgr.get_solution(papernum, verbose=verbose)


@with_messenger
def get_all_solutions(
    *, dirname: str = "solutions", msgr, verbose: bool = False
) -> dict[str, Any]:
    """Get solution files for all papers."""
    pqvmap_dict = msgr.get_pqvmap()
    papernum_list = [int(papernum) for papernum in pqvmap_dict.keys()]

    return _get_all_helper(
        papernum_list,
        msgr.get_solution,
        dirname=dirname,
        verbose=verbose,
    )


@with_messenger
def get_all_reassembled(
    *, dirname: str = "reassembled", msgr, verbose: bool = False
) -> dict[str, Any]:
    """Get all papers in their marked states."""
    pqvmap_dict = msgr.get_pqvmap()
    papernum_list = [int(papernum) for papernum in pqvmap_dict.keys()]

    return _get_all_helper(
        papernum_list,
        msgr.get_reassembled,
        dirname=dirname,
        verbose=verbose,
    )


@with_messenger
def get_all_unmarked(
    *, dirname: str = "unmarked", msgr, verbose: bool = False
) -> dict[str, Any]:
    """Get all papers in their unmarked states."""
    pqvmap_dict = msgr.get_pqvmap()
    papernum_list = [int(papernum) for papernum in pqvmap_dict.keys()]

    return _get_all_helper(
        papernum_list,
        msgr.get_unmarked,
        dirname=dirname,
        verbose=verbose,
    )


def _get_all_helper(
    papernum_list: list[int], msgr_func, *, dirname: str, verbose=False
) -> dict[str, Any]:
    """A helper to call messenger functions across 'all' papers.

    Args:
        papernum_list: a list of 'all' paper numbers.
        msgr_func: a bound PlomAdminMessenger function. It will be executed
            over all items in papernum_list.

    Keyword Args:
        dirname: what to name the directory containing the downloaded files.
            This cannot be the name of an existing directory.
        msgr: a PlomAdminMessenger instance
        verbose: whether extra information should be written to stdout

    Raises:
        OSError: directory 'dirname/' already exists or cannot be written to.
    """
    previous_cwd = getcwd()
    paper_count = 0
    content_length = 0

    mkdir(dirname)  # this raises an error if dirname/ already exists
    chdir(dirname)
    for papernum in tqdm(papernum_list):
        try:
            r = msgr_func(papernum, verbose=verbose)
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
