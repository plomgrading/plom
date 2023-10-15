# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2023 Colin B. Macdonald

import csv
import json
from pathlib import Path
from typing import Dict, Union

from plom import undo_json_packing_of_version_map, check_version_map
from plom.create import with_manager_messenger


def _version_map_from_json(f: Path) -> Dict:
    with open(f, "r") as fh:
        qvmap = json.load(fh)
    qvmap = undo_json_packing_of_version_map(qvmap)
    check_version_map(qvmap)
    return qvmap


def _version_map_from_csv(f: Path) -> Dict[int, Dict[int, int]]:
    """Extract the version map from a csv file.

    Args:
        f: a csv file, must have a `test_number` column
            and some `q{n}.version` columns.  The number of such columns
            is autodetected.  For example, this could be output of
            :func:`save_question_version_map`.

    Returns:
        dict: keys are the paper numbers (`int`) and each value is a row
        of the version map: another dict with questions as question
        number (`int`) and value version (`int`).

    Raises:
        ValueError: values could not be converted to integers, or
            other errors in the version map.
        KeyError: wrong column header names.
    """
    qvmap = {}
    with open(f, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        N = len(reader.fieldnames) - 1
        for row in reader:
            testnum = int(row["test_number"])
            qvmap[testnum] = {n: int(row[f"q{n}.version"]) for n in range(1, N + 1)}
    check_version_map(qvmap)
    return qvmap


def version_map_from_file(f: Union[Path, str]) -> Dict[int, Dict[int, int]]:
    """Extract the version map from a csv or json file.

    Args:
        f: If ``.csv`` file, must have a `test_number`
            column and some `q{n}.version` columns.  The number of such
            columns is autodetected.  If ``.json`` file, its a dict of
            dicts.  Either case could, for example, be the output of
            :func:`save_question_version_map`.

    Returns:
        keys are the paper numbers (`int`) and each value is a row
        of the version map: another dict with questions as question
        number (`int`) and value version (`int`).

    Raises:
        ValueError: values could not be converted to integers, or
            other errors in the version map.
        KeyError: wrong column header names.
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


def _version_map_to_csv(qvmap: Dict, filename: Path) -> None:
    """Output a csv of the question-version map.

    Arguments:
        qvmap: the question-version map, documented elsewhere.
        filename: where to save.

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

    Return:
        dict: keys are the paper numbers (`int`) and each value is a row
        of the version map: another dict with questions as question
        number (`int`) and value version (`int`).

    Raises:
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

    Return:
        pathlib.Path: the name of the file saved.

    Raises:
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
