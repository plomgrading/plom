# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2024 Colin B. Macdonald

import json
from pathlib import Path
from typing import Dict

from plom import version_map_to_csv
from plom.create import with_manager_messenger


@with_manager_messenger
def download_version_map(*, msgr) -> Dict[int, Dict[int, int]]:
    """Get the question-version map from a server.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    Returns:
        keys are the paper numbers (`int`) and each value is a row
        of the version map: another dict with questions as question
        number (`int`) and value version (`int`).

    Raises:
        PlomServerNotReady
    """
    return msgr.getGlobalQuestionVersionMap()


@with_manager_messenger
def save_version_map(filename=None, *, msgr) -> Path:
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

    Returns:
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
        version_map_to_csv(qvmap, filename)
    elif suffix.casefold() == ".json":
        with open(filename, "w") as f:
            json.dump(qvmap, f, indent="  ")
    else:
        raise NotImplementedError(f'Don\'t know how to export to "{filename}"')
    return filename
