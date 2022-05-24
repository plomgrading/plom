# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018-2022 Colin B. Macdonald

import functools

from plom.messenger import ManagerMessenger
from plom.plom_exceptions import PlomExistingLoginException


def start_messenger(server=None, pwd=None, verify_ssl=True):
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p, verify_ssl=verify_ssl)
    else:
        msgr = ManagerMessenger(server, verify_ssl=verify_ssl)
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


def with_manager_messenger(f):
    """Decorator for flexible credentials or open messenger.

    Arguments:
        f (function):

    Returns:
        function: the original wrapped with logging.
    """

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        # if we have a messenger, nothing special, just call function
        msgr = kwargs.get("msgr")
        if isinstance(msgr, ManagerMessenger):
            return f(*args, **kwargs)

        # if not, we assume its appropriate args to make a messenger
        credentials = kwargs.pop("msgr")
        msgr = start_messenger(*credentials)
        kwargs["msgr"] = msgr
        try:
            return f(*args, **kwargs)
        finally:
            msgr.closeUser()
            msgr.stop()

    return wrapped


def clear_manager_login(server=None, password=None):
    """Force clear the "manager" authorisation, e.g., after a crash.

    Args:
        server (str): in the form "example.com" or "example.com:41984".
        password (str): if not specified, prompt on the command line.
    """
    if server and ":" in server:
        s, p = server.split(":")
        msgr = ManagerMessenger(s, port=p)
    else:
        msgr = ManagerMessenger(server)
    msgr.start()

    msgr.clearAuthorisation("manager", password)
    print("Manager login cleared.")
    msgr.stop()
