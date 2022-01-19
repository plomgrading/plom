# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

from warnings import warn

import pandas


def version_map_from_csv(f):
    """Extract the version map from a csv file

    Args:
        f (pathlib.Path): a csv file, must have a `test_number` column
            and some `q{n}.version` columns.  The number of such columns
            is autodetected.

    Keyword Args:
        server (str/None)
        password (str/None)

    TODO: `f` could have names in it: this routine makes no use of that
    information.  In particular, it does not try to verify that they match
    the current server's classlist.
    """
    # TODO: we could get the number of versions from the spec
    # msgr.start()
    # spec = msgr.get_spec()
    # msgr.stop()
    # N = spec["numberOfVersions"]

    df = pandas.read_csv(f, dtype="object")

    N = 0
    while True:
        if f"q{N + 1}.version" not in df.columns:
            break
        N += 1
    if N == 0:
        raise ValueError(f"Could not find q1.version column in {df.columns}")

    if "sID" in df.columns or "sname" in df.columns:
        warn('Ignoring the "sID" and "sname" columns in {f}')

    qvmap = {}
    for i, r in df.iterrows():
        testnum = int(r["test_number"])
        qvmap[testnum] = {n: int(r[f"q{n}.version"]) for n in range(1, N + 1)}
    return qvmap
