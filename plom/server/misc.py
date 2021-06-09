# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

"""Misc utilities for the Plom Server"""

import logging
from pathlib import Path
import sys

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import plom
from plom import Default_Port
from plom.server import specdir, confdir


log = logging.getLogger("server")


server_dirs = (
    specdir,
    confdir,
    Path("pages"),
    Path("pages") / "discardedPages",
    Path("pages") / "collidingPages",
    Path("pages") / "unknownPages",
    Path("pages") / "originalPages",
    Path("markedQuestions"),
    Path("markedQuestions") / "plomFiles",
    Path("userRubricPaneData"),
)


def build_server_directories():
    """Build some directories the server will need"""

    for d in server_dirs:
        Path(d).mkdir(exist_ok=True)
        log.debug("Building directory {}".format(d))


def check_server_directories():
    """Ensure some server directories exist"""

    for d in server_dirs:
        if not d.is_dir():
            raise FileNotFoundError(
                "Required directory '{}' are not present. "
                "Have you run 'plom-server init'?".format(d)
            )


def create_server_config(dur=confdir, *, port=None):
    """Create a default server configuration file.

    args:
        port (int/None): port on which to run the server.
        dur (pathlib.Path): where to put the file.

    raises:
        FileExistsError: file is already there.
    """
    sd = Path(dur) / "serverDetails.toml"
    if sd.exists():
        raise FileExistsError("Config already exists in {}".format(sd))
    template = resources.read_text(plom, "serverDetails.toml")
    if port:
        template = template.replace(f"{Default_Port}", str(port))
    with open(sd, "w") as fh:
        fh.write(template)


def create_blank_predictions(dur=specdir):
    """Create empty prediction list to store machine-read student IDs.

    args:
        dur (str/pathlib.Path): where to put the file.

    raises:
        FileExistsError: file is already there.
    """
    pl = Path(dur) / "predictionlist.csv"
    if pl.exists():
        raise FileExistsError(f"{pl} already exists.")
    with open(pl, "w") as fh:
        fh.write("test, id\n")
