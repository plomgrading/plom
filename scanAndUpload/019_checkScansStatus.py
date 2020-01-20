#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import getpass
import os
import requests
import shutil
import ssl
import sys
import urllib3
import threading
import toml

# ----------------------
sys.path.append("..")
from resources.specParser import SpecParser
from resources.plom_exceptions import *
from resources.misc_utils import format_int_list_with_runs
from resources.version import Plom_API_Version

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
def requestAndSaveToken(user, pw):
    """Get a authorisation token from the server.

    The token is then used to authenticate future transactions with the server.

    """
    global _userName, _token

    SRmutex.acquire()
    try:
        print("Requesting authorisation token from server")
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


def getScannedTests():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/scanned".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token},
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return response.json()


def getUnusedTests():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/unused".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token},
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return response.json()


def getIncompleteTests():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/incomplete".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token},
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return response.json()


# ----------------------
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

    authSession = requests.Session()
    authSession.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
    requestAndSaveToken("scanner", pwd)

    spec = SpecParser().spec
    session = requests.Session()
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))

    ST = getScannedTests()  # returns pairs of [page,version] - only display pages
    UT = getUnusedTests()
    IT = getIncompleteTests()
    print("Test papers unused: [{}]".format(format_int_list_with_runs(UT)))

    print("Scanned tests in the system:")
    for t in ST:
        scannedPages = [x[0] for x in ST[t]]
        print("\t{}: [{}]".format(t, format_int_list_with_runs(scannedPages)))

    print("Incomplete scans - listed with their missing pages: ")
    for t in IT:
        missingPages = [x[0] for x in IT[t]]
        print("\t{}: [{}]".format(t, format_int_list_with_runs(missingPages)))
