# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

"""Misc utilities for the Plom Server"""

import logging
from pathlib import Path

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
    Path("markedQuestions") / "commentFiles",
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
