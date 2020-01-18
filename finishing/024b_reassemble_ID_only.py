#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later


import csv
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
import threading

# ----------------------
sys.path.append("..")
from resources.plom_exceptions import *
from resources.version import Plom_API_Version

_userName = "manager"

# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# Server defaults
server = "0.0.0.0"
message_port = 41984
SRmutex = threading.Lock()
numberOfTests = 0
numberOfQuestions = 0

# ----------------------


def requestAndSaveToken(user, pw):
    """Get a authorisation token from the server.

    The token is then used to authenticate future transactions with the server.

    """
    global _userName, _token

    SRmutex.acquire()
    try:
        response = authSession.put(
            "https://{}:{}/users/{}".format(server, message_port, user),
            json={"user": user, "pw": pw, "api": Plom_API_Version},
            verify=False,
            timeout=5,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        _token = response.json()
        _userName = user
        print("Success!")
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            print(
                "Password problem - you are not authorised to upload pages to server."
            )
        elif response.status_code == 400:  # API error
            raise PlomAPIException()
            print("An API problem - {}".format(response.json()))
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
        quit()
    except requests.ConnectionError as err:
        raise PlomSeriousException(
            "Cannot connect to\n server:port = {}:{}\n Please check details before trying again.".format(
                server, message_port
            )
        )
        quit()
    finally:
        SRmutex.release()


def closeUser():
    SRmutex.acquire()
    try:
        response = session.delete(
            "https://{}:{}/users/{}".format(server, message_port, _userName),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return True


def getInfoTPQV():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/info/numberOfTPQV".format(server, message_port),
            verify=False,
        )
        response.raise_for_status()
        tpqv = response.json()
    except requests.HTTPError as e:
        if response.status_code == 404:
            raise PlomSeriousException(
                "Server could not find the spec - this should not happen!"
            )
        elif response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return tpqv


if __name__ == "__main__":
    try:
        pwd = getpass.getpass("Please enter the 'manager' password:")
    except Exception as error:
        print("ERROR", error)

    authSession = requests.Session()
    authSession.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
    requestAndSaveToken("manager", pwd)

    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))

    pqv = getInfoTPQV()
    numberOfTests = pqv[0]
    numberOfQuestions = pqv[2]

    print(">>> This is all it does so far <<<")
