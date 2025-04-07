# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2018-2025 Colin B. Macdonald

import functools

from plom.messenger import Messenger
from plom.plom_exceptions import PlomExistingLoginException


def start_messenger(
    server: str | None,
    usr: str,
    pwd: str,
    verify_ssl: bool = True,
) -> Messenger:
    """Start and return a new messenger with a certain username and password."""
    msgr = Messenger(server, verify_ssl=verify_ssl)
    msgr.start()

    try:
        msgr.requestAndSaveToken(usr, pwd)
    except PlomExistingLoginException:
        print(
            "You appear to be already logged in!\n\n"
            "  * Perhaps a previous session crashed?\n"
            "  * Do you have another scanner-script running,\n"
            "    e.g., on another computer?\n\n"
            'In order to force-logout the existing authorisation run "plom-cli clear"'
        )
        raise
    return msgr


def with_messenger(f):
    """Decorator for flexible credentials or open messenger.

    Arguments:
        f (function): the function to be decorated.

    Returns:
        function: the original wrapped with logging.
    """

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        # if we have a messenger, nothing special, just call function
        msgr = kwargs.get("msgr")
        if isinstance(msgr, Messenger):
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


def clear_login(server: str | None, username: str, password: str) -> None:
    msgr = Messenger(server)
    msgr.start()

    try:
        msgr.clearAuthorisation(username, password)
        print(f'Login cleared for "{username}".')
    finally:
        msgr.stop()
