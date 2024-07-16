# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2023 Andrew Rechnitzer
# Copyright (C) 2021-2024 Colin B. Macdonald

"""Tools for manipulating version maps."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import random
from typing import Any

# TODO: go through and fix all the places with str(q+1)
# TODO: there is some documentation of "param" below that should move elsewhere


def check_version_map(
    vm: dict[Any, Any],
    spec=None,
    *,
    legacy: bool = False,
    required_papers: list[int] | None = None,
) -> None:
    """Correctness checks of a version maps.

    Args:
        vm (dict): a dict-of-dicts describing versions.  See the output
            of :func:`plom.make_random_version_map`.
        spec (plom.SpecVerifier/dict): a plom spec or the underlying
            dict, see :func:`plom.SpecVerifier`.

    Keyword Args:
        legacy: True if this version map is for a legacy server, which
            is more strict about contiguous range of papers for example.
        required_papers: A list of paper_numbers that the qv map must have.

    Returns:
        None

    Raises:
        ValueError
    """
    rowlens = set()
    for t, qd in vm.items():
        if not isinstance(t, int):
            raise ValueError(f'test number key "{t}" ({type(t)}) is not an integer')
        if not isinstance(qd, dict):
            raise ValueError(f'row "{qd}" of version map should be a dict')
        if spec and not len(qd) == spec["numberOfQuestions"]:
            raise ValueError(
                f"length of row {qd}  does not match numberOfQuestion in spec {spec}"
            )
        # even if no spec we can ensure all rows the same
        rowlens.add(len(qd))
        for q, v in qd.items():
            if not isinstance(q, int):
                raise ValueError(f'question key "{q}" ({type(q)}) is not an integer')
            if not isinstance(v, int):
                raise ValueError(f'version "{v}" ({type(v)}) should be an integer')
            if not v > 0:
                raise ValueError(f'version "{v}" should be strictly positive')
            if spec:
                if not v <= spec["numberOfVersions"]:
                    raise ValueError(
                        f'version "{v}" should be less than numberOfVersions in spec {spec}'
                    )
                # TODO: unsure about this: maybe we should doc that we ignore "select"
                # when custom version maps are used
                if spec["question"][str(q)]["select"] == "fix":
                    if not v == 1:
                        raise ValueError(
                            f'version "{v}" is not 1 but question is "fix" in spec {spec}'
                        )

    if not len(rowlens) <= 1:
        raise ValueError("Inconsistency in version map: not all rows had same length")

    # check if required papers are all present
    if required_papers:
        missing_papers = [X for X in required_papers if X not in vm]
        if missing_papers:
            raise ValueError(
                f"Map is missing required papers: {missing_papers}. These were likely prenamed papers"
            )

    if not legacy:
        return
    # remaining checks should matter only for legacy servers
    if spec and not len(vm) == spec["numberToProduce"]:
        raise ValueError(
            f"Legacy server requires numberToProduce={spec['numberToProduce']}"
            f" to match the number of rows {len(vm)} of the version map"
        )
    if vm.keys():
        min_testnum = min(vm.keys())
        max_testnum = max(vm.keys())
        if not min_testnum == 1:
            raise ValueError(f"test_number should start at 1: got {list(vm.keys())}")
        if not set(vm.keys()) == set(range(min_testnum, max_testnum + 1)):
            raise ValueError(f"No gaps allowed in test_num: got {list(vm.keys())}")


def make_random_version_map(
    spec, *, seed: str | None = None
) -> dict[int, dict[int, int]]:
    """Build a random version map.

    Args:
        spec (plom.SpecVerifier/dict): A plom exam specification or the
            underlying dict.  See :func:`plom.SpecVerifier`.  The most
            important properties are the `numberToProduce`, the
            `numberOfQuestions`, and the `select` of each question.

    Keyword Args:
        seed: to get a reproducible version map, we can seed the
            pseudo-random number generator.  Unknown how portable this
            is between Python versions or OSes.

    Returns:
        dict: a dict-of-dicts keyed by paper number (int) and then
            question number (int, but indexed from 1 not 0).  Values are
            integers.

    Raises:
        KeyError: invalid question selection scheme in spec.
    """
    if seed is not None:
        random.seed(seed)

    # we want to have nearly equal numbers of each version - issue #1470
    # first make a list which cycles through versions
    vlist = [(x % spec["numberOfVersions"]) + 1 for x in range(spec["numberToProduce"])]
    # now assign a copy of this for each question, so qvlist[question][testnumber]=version
    qvlist = [
        random.sample(vlist, len(vlist)) for q in range(spec["numberOfQuestions"])
    ]
    # we use the above when a question is shuffled, else we just use v=1.

    vmap: dict[int, dict[int, int]] = {}
    for t in range(1, spec["numberToProduce"] + 1):
        vmap[t] = {}
        for g in range(spec["numberOfQuestions"]):  # runs from 0,1,2,...
            gs = str(g + 1)  # now a str and 1,2,3,...
            if spec["question"][gs]["select"] == "fix":
                # there is only one version so all are version 1
                vmap[t][g + 1] = 1
            elif spec["question"][gs]["select"] == "shuffle":
                # version selected randomly in [1, 2, ..., #versions]
                # the below is purely random, so uneven distribution of versions
                # vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
                # replace with more equal distribution of versions from qvlist above
                vmap[t][g + 1] = qvlist[g][t - 1]
                # offset by one due to indices starting from 0

            # TODO: we may enable something like this later
            # elif spec["question"][gs]["select"] == "param":
            #    # If caller does not provide a version, all are version 1.
            #    # Caller can provide a version to group their parameters by any
            #    # way they wish.  Typically this would be be ease grading, e.g.,
            #    #   * map negative parameters to v1 and positive to v2.
            #    #   * map tuples (a,b) with common `b` value to same version.
            #    # In fact there is no significant difference between `param`
            #    # and `shuffle` when user data is provided.  But clients or
            #    # other aspects of the software might behave differently.
            #    vmap[t][g + 1] = random.randint(1, spec["numberOfVersions"])
            else:
                raise KeyError(
                    'Invalid spec: question {} "select" of "{}" is unexpected'.format(
                        gs, spec["question"][gs]["select"]
                    )
                )
    return vmap


def undo_json_packing_of_version_map(
    vermap_in: dict[str, dict[str, int]],
) -> dict[int, dict[int, int]]:
    """JSON must have string keys; undo such to int keys for version map.

    Both the test number and the question number have likely been
    converted to strings by an evil JSON: we build a new dict-of-dicts
    with both converted explicitly to integers.

    Note: sometimes the dict-of-dicts is key'd by page number instead
    of question number.  This same function can be used in that case.
    """
    vmap = {}
    for t, question_vers in vermap_in.items():
        vmap[int(t)] = {int(q): v for q, v in question_vers.items()}
    return vmap


def _version_map_from_json(
    f: Path, *, required_papers: list[int] | None = None
) -> dict:
    with open(f, "r") as fh:
        qvmap = json.load(fh)
    qvmap = undo_json_packing_of_version_map(qvmap)
    check_version_map(qvmap, required_papers=required_papers)
    return qvmap


def _version_map_from_csv(
    f: Path, *, required_papers: list[int] | None = None
) -> dict[int, dict[int, int]]:
    """Extract the version map from a csv file.

    Args:
        f: a csv file, must have a `test_number` column
            and some `q{n}.version` columns.  The number of such columns
            is autodetected.  For example, this could be output of
            :func:`save_question_version_map`.

    Keyword Args:
        required_papers: A list of paper_numbers that the qv map must have.

    Returns:
        dict: keys are the paper numbers (`int`) and each value is a row
        of the version map: another dict with questions as question
        number (`int`) and value version (`int`).

    Raises:
        ValueError: values could not be converted to integers, or
            other errors in the version map.
        KeyError: wrong column header names.
    """
    qvmap: dict[int, dict[int, int]] = {}

    with open(f, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        if not reader.fieldnames:
            raise ValueError("csv must have column names")
        N = len(reader.fieldnames) - 1
        for line, row in enumerate(reader):
            # Its called "test_number" on legacy and "paper_number" on webplom
            # raise a value error if you cannot find either.
            if "paper_number" in row:
                papernum = int(row["paper_number"])
            elif "test_number" in row:
                papernum = int(row["test_number"])
            else:
                raise ValueError("Cannot find paper_number column")

            if papernum in qvmap.keys():
                raise ValueError(
                    f"In line {line} Duplicate paper number detected: {papernum}"
                )
            try:
                qvmap[papernum] = {
                    n: int(row[f"q{n}.version"]) for n in range(1, N + 1)
                }
            except KeyError as err:
                raise KeyError(f"Missing column header {err}")
            except ValueError as err:
                raise ValueError(f"In line {line}: {err}")

    check_version_map(qvmap, required_papers=required_papers)
    return qvmap


def version_map_from_file(
    f: Path | str, *, required_papers: list[int] | None = None
) -> dict[int, dict[int, int]]:
    """Extract the version map from a csv or json file.

    Args:
        f: If ``.csv`` file, must have a `test_number`
            column and some `q{n}.version` columns.  The number of such
            columns is autodetected.  If ``.json`` file, its a dict of
            dicts.  Either case could, for example, be the output of
            :func:`save_question_version_map`.

    Keyword Args:
        required_papers: A list of paper_numbers that the qv map must have.

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
        f = f.with_suffix(f.suffix + ".csv")
    suffix = f.suffix

    if suffix.casefold() == ".json":
        return _version_map_from_json(f, required_papers=required_papers)
    elif suffix.casefold() == ".csv":
        return _version_map_from_csv(f, required_papers=required_papers)
    else:
        raise NotImplementedError(f'Don\'t know how to import from "{f}"')


def version_map_to_csv(
    qvmap: dict[int, dict[int, int]], filename: Path, *, _legacy: bool = True
) -> None:
    """Output a csv of the question-version map.

    Arguments:
        qvmap: the question-version map, documented elsewhere.
        filename: where to save.

    Keyword Args:
        _legacy: if True, we call the column "test_number" else "paper_number".
            Currently the default is True but this is expected to change.

    Raises:
        ValueError: some rows have differing numbers of questions.
    """
    # all rows should have same length: get than length or fail
    (N,) = {len(v) for v in qvmap.values()}

    if _legacy:
        header = ["test_number"]
    else:
        header = ["paper_number"]
    for q in range(1, N + 1):
        header.append(f"q{q}.version")
    with open(filename, "w") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(header)
        for k, v in qvmap.items():
            csv_writer.writerow([k, *[v[q] for q in range(1, N + 1)]])
