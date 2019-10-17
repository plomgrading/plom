# -*- coding: utf-8 -*-

"""
Utility functions related to clients
"""

__author__ = "Andrew Rechnitzer, Colin B. Macdonald"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer, Colin B. Macdonald"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys

import messenger

sys.path.append("..")  # this allows us to import from ../resources
from resources.version import Plom_API_Version


def requestToken(user, pwhash):
    """Get a authorisation token from the server

    The request sends name and password (over ssl) to the server. If
    hash of password matches the one on file, then the server sends
    back an "ACK" and an authentication token. The token is then used
    to authenticate future transactions with the server (since
    password hashing is slow).

    Returns the token or raises a ValueError with message from the server.
    """
    [msg, token] = messenger.SRMsg(["AUTH", user, pwhash, Plom_API_Version])
    # Return should be [ACK, token]
    if not msg == "ACK":
        raise ValueError(token)
    return token
