# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

"""SSL and related utilities for the Plom Server"""

import locale
import logging
from pathlib import Path
import subprocess
import shlex

from plom.server import confdir


log = logging.getLogger("server")


def build_self_signed_SSL_keys(dir=confdir, extra_args=""):
    """Make new self-signed key and cert files if they do not yet exist.

    Calls the `openssl` binary using `subprocess`.

    args:
        dir (pathlib.Path): where to put the key and cert file.
        extra_args (str): any extra command line args for openssl.

    raises:
        RuntimeError: on subprocess failure.
    """
    key = Path(dir) / "plom.key"
    cert = Path(dir) / "plom-selfsigned.crt"
    if key.is_file() and cert.is_file():
        raise FileExistsError("SSL key and certificate already exist")

    # Generate new self-signed key/cert
    sslcmd = "openssl req -x509 -sha256 -newkey rsa:2048"
    sslcmd += " -keyout {} -nodes -out {} -days 1000 -subj".format(key, cert)

    sslcmd += " {}".format(extra_args)

    # TODO: is this the way to get two digit country code?
    tmp = locale.getdefaultlocale()[0]
    if tmp:
        twodigcc = tmp[-2:]
    else:
        twodigcc = "CA"
    sslcmd += " '/C={}/ST=./L=./CN=localhost'".format(twodigcc)
    try:
        subprocess.check_call(shlex.split(sslcmd))
    except (FileNotFoundError, subprocess.CalledProcessError) as err:
        raise RuntimeError("Something went wrong building SSL keys") from err
