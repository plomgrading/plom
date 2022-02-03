# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018-2022 Colin B. Macdonald

import functools

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException


def start_messenger(server=None, pwd=None, verify=True):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p, verify=verify)
    else:
        msgr = ManagerMessenger(server, verify=verify)
    msgr.start()

    try:
        msgr.requestAndSaveToken("manager", pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another management tool running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-create clear"'
        )
        raise
    return msgr


def with_messenger(f):
    """Decorator for flexible credentials or open messenger.

    Arguments:
        f (function):

    Returns:
        function: the original wrapped with logging.
    """

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        cred = kwargs.pop("cred", None)
        if not cred:
            if not kwargs.get("msgr"):
                raise ValueError("Must provide 'cred=' or 'msgr='")
            return f(*args, **kwargs)

        if kwargs.get("msgr"):
            raise ValueError("Cannot provide both 'cred=' AND 'msgr='")
        msgr = start_messenger(*cred)
        kwargs[msgr] = msgr
        try:
            return f(*args, **kwargs)
        finally:
            msgr.closeUser()
            msgr.stop()

    return wrapped
