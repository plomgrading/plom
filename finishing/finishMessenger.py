#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
import requests
from requests_toolbelt import MultipartEncoder
import ssl
import threading
import toml
import urllib3

from plom_exceptions import *
from version import Plom_API_Version

_userName = "manager"

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
session = None


def getServerInfo():
    global server
    global message_port
    if os.path.isfile("server.toml"):
        with open("server.toml") as fh:
            si = toml.load(fh)
        server = si["server"]
        message_port = si["port"]


def requestAndSaveToken(user, pw):
    """Get a authorisation token from the server.

    The token is then used to authenticate future transactions with the server.

    """
    global _userName, _token

    SRmutex.acquire()
    try:
        response = session.put(
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
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.") from None
        elif response.status_code == 400:  # API error
            raise PlomAPIException(response.json()) from None
        elif response.status_code == 409:
            raise PlomExistingLoginException(response.json()) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    except requests.ConnectionError as err:
        raise PlomSeriousException(
            "Cannot connect to\n server:port = {}:{}\n Please check details before trying again.".format(
                server, message_port
            )
        ) from None
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


def clearAuthorisation(user, password=None):
    SRmutex.acquire()
    try:
        if user == "manager":
            response = session.delete(
                "https://{}:{}/authorisation".format(server, message_port),
                json={"user": user, "password": password, "userToClear": user},
                verify=False,
            )
        else:
            response = session.delete(
                "https://{}:{}/authorisation".format(server, message_port),
                json={"user": _userName, "token": _token, "userToClear": user},
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


def getInfoShortName():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/info/shortName".format(server, message_port), verify=False
        )
        response.raise_for_status()
        shortName = response.text
    except requests.HTTPError as e:
        if response.status_code == 404:
            raise PlomSeriousException(
                "Server could not find the spec - this should not happen!"
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return shortName


def getInfoGeneral():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/info/general".format(server, message_port), verify=False,
        )
        response.raise_for_status()
        pv = response.json()
    except requests.HTTPError as e:
        if response.status_code == 404:
            raise PlomSeriousException(
                "Server could not find the spec - this should not happen!"
            )
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    fields = (
        "testName",
        "numberOfTests",
        "numberOfPages",
        "numberOfQuestions",
        "numberOfVersions",
        "publicCode",
    )
    return dict(zip(fields, pv))


def RgetCompletions():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/completions".format(server, message_port),
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


def RgetSpreadsheet():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/spreadSheet".format(server, message_port),
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


def RgetIdentified():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/identified".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token,},
        )
        response.raise_for_status()
        rval = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return rval


def RgetCompletions():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/completions".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token,},
        )
        response.raise_for_status()
        rval = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return rval


def RgetCoverPageInfo(test):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/coverPageInfo/{}".format(server, message_port, test),
            verify=False,
            json={"user": _userName, "token": _token,},
        )
        response.raise_for_status()
        rval = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return rval


def RgetAnnotatedFiles(testNumber):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/annotatedFiles/{}".format(
                server, message_port, testNumber
            ),
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


def MgetAllMax():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/allMax".format(server, message_port),
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


def startMessenger(altServer=None, altPort=None):
    """Start the messenger session"""
    print("Starting a requests-session")
    global authSession
    global session
    global server
    global message_port
    if altServer is not None:
        server = altServer
    if altPort is not None:
        message_port = altPort

    authSession = requests.Session()
    session = requests.Session()
    # set max_retries to large number because UBC-wifi is pretty crappy.
    # TODO - set smaller number and have some sort of "hey you've retried
    # nn times already, are you sure you want to keep retrying" message.
    authSession.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))


def stopMessenger():
    """Stop the messenger"""
    print("Stopped messenger session")
    session.close()
    authSession.close()
