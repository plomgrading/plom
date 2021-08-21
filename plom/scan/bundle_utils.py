# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

import hashlib
from pathlib import Path
import shutil

import toml

archivedir = Path("archivedPDFs")
# TODO: not yet used by callers
_main_bundledir = Path("bundles")


def make_base_directories():
    """Make various directories that bundle uploading will need.

    args:
        bundle (None/pathlib.Path)
    """
    archivedir.mkdir(exist_ok=True)
    (archivedir / Path("submittedHWByQ")).mkdir(exist_ok=True)
    (archivedir / Path("submittedLoose")).mkdir(exist_ok=True)
    _main_bundledir.mkdir(exist_ok=True)
    # deprecated
    (_main_bundledir / "submittedLoose").mkdir(exist_ok=True)


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


def bundle_name_from_file(filename):
    """Return the bundle name for a file.

    Args:
        filename (str, Path): name of file, typically a PDF file.

    Returns
        str: Currently bundle name is the stem of the file name with
            some input sanitizing such as spaces replaced with underscores.
    """
    filename = Path(filename)
    return filename.stem.replace(" ", "_")


def bundle_name_and_md5_from_file(filename):
    """Return the bundle name and md5sum checksum for a file.

    Args:
        filename (str/Path): name of file.

    Returns
        tuple: (str, str) for bundle_name and md5sum.

    Exceptions:
        FileNotFoundError: file does not exist.
    """
    filename = Path(filename)
    if not filename.is_file():
        raise FileNotFoundError("not found or not a file/symlink")
    bundle_name = bundle_name_from_file(filename)
    md5 = hashlib.md5(open(filename, "rb").read()).hexdigest()
    return (bundle_name, md5)


def _archiveBundle(file_name, this_archive_dir):
    """Archive the bundle pdf.

    The bundle.pdf is moved into the appropriate archive directory
    as given by this_archive_dir. The archive.toml file is updated
    with the name and md5sum of that bundle.pdf.
    """
    md5 = hashlib.md5(open(file_name, "rb").read()).hexdigest()
    shutil.move(file_name, this_archive_dir / Path(file_name).name)
    try:
        arch = toml.load(archivedir / "archive.toml")
    except FileNotFoundError:
        arch = {}
    arch[md5] = str(file_name)
    # now save it
    with open(archivedir / "archive.toml", "w+") as fh:
        toml.dump(arch, fh)


def archiveHWBundle(file_name):
    """Archive a hw-pages bundle pdf"""
    print("Archiving homework bundle {}".format(file_name))
    _archiveBundle(file_name, archivedir / "submittedHWByQ")


def archiveLBundle(file_name):
    """Archive a loose-pages bundle pdf"""
    print("Archiving loose-page bundle {}".format(file_name))
    _archiveBundle(file_name, archivedir / "submittedLoose")


def archiveTBundle(file_name):
    """Archive a test-pages bundle pdf"""
    print("Archiving test-page bundle {}".format(file_name))
    _archiveBundle(file_name, archivedir)
