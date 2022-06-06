# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald

import csv
import json
from pathlib import Path
from warnings import warn

# try to avoid importing Pandas unless we use specific functions: Issue #2154
# import pandas

from plom import undo_json_packing_of_version_map, check_version_map
from plom.create import with_manager_messenger


def _version_map_from_json(f):
    with open(f, "r") as fh:
        qvmap = json.load(fh)
    qvmap = undo_json_packing_of_version_map(qvmap)
    check_version_map(qvmap)
    return qvmap


def _version_map_from_csv(f):
    """Extract the version map from a csv file

    Args:
        f (pathlib.Path): a csv file, must have a `test_number` column
            and some `q{n}.version` columns.  The number of such columns
            is autodetected.  For example, this could be output of
            :func:`save_question_version_map`.

    Return:
        dict: keys are the paper numbers (`int`) and each value is a row
        of the version map: another dict with questions as question
        number (`int`) and value version (`int`).

    TODO: `f` could have names in it: this routine makes no use of that
    information.  In particular, it does not try to verify that they match
    the current server's classlist.
    """
    import pandas

    df = pandas.read_csv(f, dtype="object")

    # autodetect number of questions from column headers
    N = 0
    while True:
        if f"q{N + 1}.version" not in df.columns:
            break
        N += 1
    if N == 0:
        raise ValueError(f"Could not find q1.version column in {df.columns}")

    if "sID" in df.columns or "sname" in df.columns:
        warn(f'Ignoring the "sID" and "sname" columns in {f}')

    qvmap = {}
    for i, r in df.iterrows():
        testnum = int(r["test_number"])
        qvmap[testnum] = {n: int(r[f"q{n}.version"]) for n in range(1, N + 1)}
    return qvmap


def version_map_from_file(f):
    """Extract the version map from a csv or json file.

    Args:
        f (pathlib.Path): If ``.csv`` file, must have a `test_number`
            column and some `q{n}.version` columns.  The number of such
            columns is autodetected.  If ``.json`` file, its a dict of
            dicts.  Either case could, for example, be the output of
            :func:`save_question_version_map`.

    Return:
        dict: keys are the paper numbers (`int`) and each value is a row
        of the version map: another dict with questions as question
        number (`int`) and value version (`int`).
    """
    f = Path(f)
    if f.suffix.casefold() not in (".json", ".csv"):
        filename = f.with_suffix(f.suffix + ".csv")
    suffix = f.suffix

    if suffix.casefold() == ".json":
        return _version_map_from_json(f)
    elif suffix.casefold() == ".csv":
        return _version_map_from_csv(f)
    else:
        raise NotImplementedError(f'Don\'t know how to import from "{filename}"')


def _version_map_to_csv(qvmap, filename):
    """Output a csv of the question-version map.

    Arguments:
        qvmap (dict): the question-version map, documented elsewhere.
        filename (pathlib.Path): where to save.

    Raises:
        ValueError: some rows have differing numbers of questions.
    """
    # all rows should have same length: get than length or fail
    (N,) = {len(v) for v in qvmap.values()}

    header = ["test_number"]
    for q in range(1, N + 1):
        header.append(f"q{q}.version")
    with open(filename, "w") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(header)
        for k, v in qvmap.items():
            csv_writer.writerow([k, *[v[q] for q in range(1, N + 1)]])


@with_manager_messenger
def download_version_map(*, msgr):
    """Get the question-version map from a server.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    return:
        dict: keys are the paper numbers (`int`) and each value is a row
        of the version map: another dict with questions as question
        number (`int`) and value version (`int`).

    raises:
        PlomServerNotReady
    """
    return msgr.getGlobalQuestionVersionMap()


@with_manager_messenger
def save_version_map(filename=None, *, msgr):
    """Get the question-version map and save to a file.

    Args:
        filename (pathlib.Path/str): a file name and optionally path
            in which to save the version map.  The extension is used to
            determine what format, supporting: ``.json`` and ``.csv``.
            If no extension is included, default to `.csv`.
            If filename omitted, default to ``question_version_map.csv``.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    return:
        pathlib.Path: the name of the file saved.

    raises:
        PlomServerNotReady

    Note if you specify ``.json``, the paper numbers and questions
    numbers will be converted to strings due to JSON limitations.
    """
    if not filename:
        filename = "question_version_map.csv"
    filename = Path(filename)
    if filename.suffix.casefold() not in (".json", ".csv"):
        filename = filename.with_suffix(filename.suffix + ".csv")
    suffix = filename.suffix

    qvmap = download_version_map(msgr=msgr)
    if suffix.casefold() == ".csv":
        _version_map_to_csv(qvmap, filename)
    elif suffix.casefold() == ".json":
        with open(filename, "w") as f:
            json.dump(qvmap, f, indent="  ")
    else:
        raise NotImplementedError(f'Don\'t know how to export to "{filename}"')
    return filename
