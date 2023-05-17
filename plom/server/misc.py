# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2021 Nicholas J H Lai

"""Misc utilities for the Plom Server"""

import logging
from pathlib import Path
import sys

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

import plom
from plom import Default_Port
from plom.server import specdir, confdir


server_dirs = (
    Path("."),
    specdir,
    confdir,
    Path("pages"),
    Path("pages") / "discardedPages",
    Path("pages") / "collidingPages",
    Path("pages") / "unknownPages",
    Path("pages") / "originalPages",
    Path("markedQuestions"),
    Path("userRubricPaneData"),
    Path("solutionImages"),
)


def build_server_directories(basedir=Path(".")):
    """Build some directories the server will need"""
    log = logging.getLogger("server")
    for d in server_dirs:
        log.debug("Making directory {}".format(d))
        (basedir / d).mkdir(exist_ok=True)


def check_server_directories(basedir=Path(".")):
    """Ensure some server directories exist"""

    for d in server_dirs:
        if not (basedir / d).is_dir():
            raise FileNotFoundError(
                "Required directory '{}' are not present. "
                "Have you run 'plom-server init'?".format(d)
            )


def check_server_fully_configured(basedir):
    if not (basedir / confdir / "serverDetails.toml").exists():
        raise FileNotFoundError(
            "Server configuration file not present. Have you run 'plom-server init'?"
        )
    if not ((basedir / confdir).glob("*.key") and (basedir / confdir).glob("*.crt")):
        raise FileNotFoundError(
            "SSL keys not present. Have you run 'plom-server init'?"
        )


def create_server_config(dur=confdir, *, port=None, name=None, db_name=None):
    """Create a default server configuration file.

    args:
        dur (pathlib.Path): where to put the file.

    keyword args:
        port (int/None): port on which to run the server.
        name (str/None): the name of your server such as
            "plom.example.com" or an IP address.  Defaults to
            "localhost" which is usually fine but may cause trouble
            with SSL certificates.
        db_name (str/None): the name of the database, omitted if `None`.

    raises:
        FileExistsError: file is already there.

    TODO: note the toml file is manipulated here with find-and-replace
    so as to preserve comments in the template.
    """
    sd = Path(dur) / "serverDetails.toml"
    if sd.exists():
        raise FileExistsError("Config already exists in {}".format(sd))
    template = (resources.files(plom) / "serverDetails.toml").read_text()
    if name:
        template = template.replace("localhost", name)
    if port:
        template = template.replace(f"{Default_Port}", str(port))
    if db_name:
        template = template.replace("#db_name =", f'db_name = "{db_name}"')
    with open(sd, "w") as fh:
        fh.write(template)
