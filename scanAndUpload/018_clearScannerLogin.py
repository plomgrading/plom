#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from glob import glob
import getpass
import hashlib
import json
import os
import requests
from requests_toolbelt import MultipartEncoder
import shutil
import ssl
import sys
import urllib3
import toml
import threading

# ----------------------
from plom_exceptions import *

sys.path.append("..")
from specParser import SpecParser
from version import Plom_API_Version

_userName = "scanner"

# ----------------------


# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# Server defaults
server = "0.0.0.0"
message_port = 41984
SRmutex = threading.Lock()


# ----------------------


def clearAuthorisation(user, pw):
    SRmutex.acquire()
    try:
        response = session.delete(
            "https://{}:{}/authorisation".format(server, message_port),
            json={"user": user, "password": pw},
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()


def getServerInfo():
    global server
    global message_port
    if os.path.isfile("server.toml"):
        with open("server.toml") as fh:
            si = toml.load(fh)
        server = si["server"]
        message_port = si["port"]


if __name__ == "__main__":
    getServerInfo()
    print("Uploading to {} port {}".format(server, message_port))
    try:
        pwd = getpass.getpass("Please enter the 'scanner' password:")
    except Exception as error:
        print("ERROR", error)

    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))

    clearAuthorisation("scanner", pwd)
    print("Scanner login cleared.")
