# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from pathlib import Path


archivedir = Path("archivedPDFs")
# TODO: not yet used by callers
bundledir = Path("bundles")


def make_base_directories():
    """Make various directories that bundle uploading will need.

    args:
        bundle (None/pathlib.Path)
    """
    archivedir.mkdir(exist_ok=True)
    (archivedir / Path("submittedHWByQ")).mkdir(exist_ok=True)
    (archivedir / Path("submittedLoose")).mkdir(exist_ok=True)
    bundledir.mkdir(exist_ok=True)
    # deprecated
    (bundledir / "submittedLoose").mkdir(exist_ok=True)


def make_bundle_dir(bundle):
    """Make various directories that processing/uploading will need.

    # TODO: I wonder if bundle should be the bundle_name not the
    # TODO: path and we'll stick a "bundledir" infront?

    args:
        bundle (pathlib.Path): the path to the bundle, either relative
            to the CWD or a full path.
    """
    make_base_directories()
    if bundle:
        for d in (
            "pageImages",
            "scanPNGs",
            "decodedPages",
            "unknownPages",
            "uploads/sentPages",
            "uploads/discardedPages",
            "uploads/collidingPages",
            "uploads/sentPages/unknowns",
            "uploads/sentPages/collisions",
        ):
            (bundle / Path(d)).mkdir(parents=True, exist_ok=True)
