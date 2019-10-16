#!/usr/bin/env python3
# -*- coding: utf-8; -*-
#
# Copyright (C) 2019 Colin B. Macdonald <cbm@m.fsf.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

__author__ = "Colin Macdonald"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__license__ = "AGPLv3"

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
