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


def uploadKnownPage(code, test, page, version, sname, fname, md5sum):
    SRmutex.acquire()
    try:
        param = {
            "user": _userName,
            "token": _token,
            "fileName": sname,
            "test": test,
            "page": page,
            "version": version,
            "md5sum": md5sum,
        }
        dat = MultipartEncoder(
            fields={
                "param": json.dumps(param),
                "originalImage": (sname, open(fname, "rb"), "image/png"),  # image
            }
        )
        response = session.put(
            "https://{}:{}/admin/knownPages/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token,},
            data=dat,
            headers={"Content-Type": dat.content_type},
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

    return response.json()


def uploadUnknownPage(sname, fname, md5sum):
    SRmutex.acquire()
    try:
        param = {
            "user": _userName,
            "token": _token,
            "fileName": sname,
            "md5sum": md5sum,
        }
        dat = MultipartEncoder(
            fields={
                "param": json.dumps(param),
                "originalImage": (sname, open(fname, "rb"), "image/png"),  # image
            }
        )
        response = session.put(
            "https://{}:{}/admin/unknownPages".format(server, message_port),
            data=dat,
            headers={"Content-Type": dat.content_type},
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

    return response.json()


def uploadCollidingPage(code, test, page, version, sname, fname, md5sum):
    SRmutex.acquire()
    try:
        param = {
            "user": _userName,
            "token": _token,
            "fileName": sname,
            "test": test,
            "page": page,
            "version": version,
            "md5sum": md5sum,
        }
        dat = MultipartEncoder(
            fields={
                "param": json.dumps(param),
                "originalImage": (sname, open(fname, "rb"), "image/png"),  # image
            }
        )
        response = session.put(
            "https://{}:{}/admin/collidingPages/{}".format(server, message_port, code),
            data=dat,
            headers={"Content-Type": dat.content_type},
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

    return response.json()


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
