# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald

"""SSL and related utilities for the Plom Server"""

import locale
from pathlib import Path
import subprocess
import shlex

from plom.server import confdir


def build_self_signed_SSL_keys(dur=confdir, extra_args=""):
    """Make new self-signed key and cert files if they do not yet exist.

    Calls the `openssl` binary using `subprocess`.

    args:
        dur (pathlib.Path): where to put the key and cert file.
        extra_args (str): any extra command line args for openssl.

    raises:
        RuntimeError: on subprocess failure.
        FileExistsError: keys are already there.
    """
    key = Path(dur) / "plom-selfsigned.key"
    cert = Path(dur) / "plom-selfsigned.crt"
    if key.is_file() and cert.is_file():
        raise FileExistsError("SSL key and certificate already exist")

    # Generate new self-signed key/cert
    sslcmd = "openssl req -x509 -sha256 -newkey rsa:2048"
    sslcmd += " -keyout {} -nodes -out {} -days 1000 -subj".format(key, cert)

    sslcmd += " {}".format(extra_args)

    # TODO: is this the way to get two digit country code?
    tmp = locale.getlocale()[0]
    if tmp:
        twodigcc = tmp[-2:]
    else:
        twodigcc = "CA"
    sslcmd += " '/C={}/ST=./L=./CN=localhost'".format(twodigcc)
    try:
        subprocess.check_call(shlex.split(sslcmd))
    except (FileNotFoundError, subprocess.CalledProcessError) as err:
        raise RuntimeError("Something went wrong building SSL keys") from err
