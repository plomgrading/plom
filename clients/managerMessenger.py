# -*- coding: utf-8 -*-

"""
Backend bits n bobs to talk to the server
"""

__author__ = "Andrew Rechnitzer, Colin B. Macdonald"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer, Colin B. Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
import requests
from requests_toolbelt import MultipartEncoder, MultipartDecoder
import json
import ssl
from PyQt5.QtWidgets import QMessageBox
import urllib3
from useful_classes import ErrorMessage
import time
import threading
import hashlib

# from http.client import HTTPConnection
# import logging
#
# logging.basicConfig()  # you need to initialize logging, otherwise you will not see anything from requests
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

from io import StringIO, BytesIO, TextIOWrapper
from plom_exceptions import *

sys.path.append("..")  # this allows us to import from ../resources
from resources.version import Plom_API_Version

# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
sslContext.check_hostname = False
# Server defaults
server = "127.0.0.1"
message_port = 41984
SRmutex = threading.Lock()
_userName = None
_token = None
session = None


def setServerDetails(s, mp):
    """Set the server IP and port"""
    global server, message_port
    server = s
    message_port = mp


def whoami():
    return _userName


# ------------------------
# ------------------------
# Authentication stuff


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
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        elif response.status_code == 400:  # API error
            raise PlomAPIException(response.json())
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    except requests.ConnectionError as err:
        raise PlomSeriousException(
            "Cannot connect to\n server:port = {}:{}\n Please check details before trying again.".format(
                server, message_port
            )
        )
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


def getInfoPQV():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/info/numberOfPQV".format(server, message_port), verify=False,
        )
        response.raise_for_status()
        pqv = response.json()
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

    return pqv


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


def getScannedTests():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/scanned".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token},
        )
        response.raise_for_status()
        rval = response.json()
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

    return rval


def getIncompleteTests():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/incomplete".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token},
        )
        response.raise_for_status()
        rval = response.json()
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

    return rval


def IDprogressCount():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/ID/progress".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        progress = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return progress


def getProgress(q, v):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/REP/progress".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token, "q": q, "v": v},
        )
        response.raise_for_status()
        rval = response.json()
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

    return rval


def replaceMissingPage(code, t, p, v):
    SRmutex.acquire()
    try:
        response = session.put(
            "https://{}:{}/admin/missingPage/{}".format(server, message_port, code),
            verify=False,
            json={
                "user": _userName,
                "token": _token,
                "test": t,
                "page": p,
                "version": v,
            },
        )
        response.raise_for_status()
        rval = response.json()
    except requests.HTTPError as e:
        if response.status_code == 404:
            raise PlomSeriousException(
                "Server could not find the TPV - this should not happen!"
            )
        elif response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return rval


def removeScannedPage(code, t, p, v):
    SRmutex.acquire()
    try:
        response = session.delete(
            "https://{}:{}/admin/scannedPage/{}".format(server, message_port, code),
            verify=False,
            json={
                "user": _userName,
                "token": _token,
                "test": t,
                "page": p,
                "version": v,
            },
        )
        response.raise_for_status()
        rval = response.json()
    except requests.HTTPError as e:
        if response.status_code == 404:
            raise PlomSeriousException(
                "Server could not find the TPV - this should not happen!"
            )
        elif response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return rval


def getUnknownPageNames():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/unknownPageNames".format(server, message_port),
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


def getDiscardNames():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/discardNames".format(server, message_port),
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


def getCollidingPageNames():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/collidingPageNames".format(server, message_port),
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


def getPageImage(t, p, v):
    code = "t{}p{}v{}".format(str(t).zfill(4), str(p).zfill(2), str(v))
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/scannedPage/{}".format(server, message_port, code),
            verify=False,
            json={
                "user": _userName,
                "token": _token,
                "test": t,
                "page": p,
                "version": v,
            },
        )
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        elif response.status_code == 404:
            return None
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return image


def getUnknownImage(fname):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/unknownImage".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token, "fileName": fname,},
        )
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        elif response.status_code == 404:
            return None
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()
    return image


def getDiscardImage(fname):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/discardImage".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token, "fileName": fname,},
        )
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        elif response.status_code == 404:
            return None
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()
    return image


def getCollidingImage(fname):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/collidingImage".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token, "fileName": fname,},
        )
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        elif response.status_code == 404:
            return None
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()
    return image


def removeUnknownImage(fname):
    SRmutex.acquire()
    try:
        response = session.delete(
            "https://{}:{}/admin/unknownImage".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token, "fileName": fname,},
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        elif response.status_code == 404:
            return False
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()
    return True


def removeCollidingImage(fname):
    SRmutex.acquire()
    try:
        response = session.delete(
            "https://{}:{}/admin/collidingImage".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token, "fileName": fname,},
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        elif response.status_code == 404:
            return False
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()
    return True


def getQuestionImages(testNumber, questionNumber):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/questionImages".format(server, message_port),
            json={
                "user": _userName,
                "token": _token,
                "test": testNumber,
                "question": questionNumber,
            },
            verify=False,
        )
        response.raise_for_status()
        # response is [image1, image2,... image.n]
        imageList = []
        for img in MultipartDecoder.from_response(response).parts:
            imageList.append(BytesIO(img.content).getvalue())

    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Cannot find image file for {}/{}.".format(testNumber, questionNumber)
            )
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return imageList


def getTestImages(testNumber):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/testImages".format(server, message_port),
            json={"user": _userName, "token": _token, "test": testNumber,},
            verify=False,
        )
        response.raise_for_status()
        # response is [image1, image2,... image.n]
        imageList = []
        for img in MultipartDecoder.from_response(response).parts:
            imageList.append(BytesIO(img.content).getvalue())

    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Cannot find image file for {}.".format(testNumber)
            )
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return imageList


def checkPage(testNumber, pageNumber):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/admin/checkPage".format(server, message_port),
            json={
                "user": _userName,
                "token": _token,
                "test": testNumber,
                "page": pageNumber,
            },
            verify=False,
        )
        response.raise_for_status()
        # response is [v, None] or [v, image1]
        vimg = MultipartDecoder.from_response(response).parts
        ver = int(vimg[0].content)
        if len(vimg) == 2:
            rval = [ver, BytesIO(vimg[1].content).getvalue()]
        else:
            rval = [ver, None]
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Cannot find image file for {}.".format(testNumber)
            )
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()
    return rval


def unknownToTestPage(fname, test, page, theta):
    SRmutex.acquire()
    try:
        response = session.put(
            "https://{}:{}/admin/unknownToTestPage".format(server, message_port),
            json={
                "user": _userName,
                "token": _token,
                "fileName": fname,
                "test": test,
                "page": page,
                "rotation": theta,
            },
            verify=False,
        )
        response.raise_for_status()
        collisionTest = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        elif response.status_code == 404:
            raise PlomSeriousException("Cannot find test/page {}.".format(tp))
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return collisionTest  # "collision" if colliding page created.


def unknownToExtraPage(fname, test, question, theta):
    SRmutex.acquire()
    try:
        response = session.put(
            "https://{}:{}/admin/unknownToExtraPage".format(server, message_port),
            json={
                "user": _userName,
                "token": _token,
                "fileName": fname,
                "test": test,
                "question": question,
                "rotation": theta,
            },
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Cannot find test/question {}/{}.".format(test, question)
            )
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()


def collidingToTestPage(fname, test, page, version):
    SRmutex.acquire()
    try:
        response = session.put(
            "https://{}:{}/admin/collidingToTestPage".format(server, message_port),
            json={
                "user": _userName,
                "token": _token,
                "fileName": fname,
                "test": test,
                "page": page,
                "version": version,
            },
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.")
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Cannot find test/page {}/{}.".format(test, page)
            )
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()


def discardToUnknown(fname):
    SRmutex.acquire()
    try:
        response = session.put(
            "https://{}:{}/admin/discardToUnknown".format(server, message_port),
            verify=False,
            json={"user": _userName, "token": _token, "fileName": fname,},
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise PlomAuthenticationException("You are not authenticated.")
        elif response.status_code == 404:
            return False
        else:
            raise PlomSeriousException("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()
    return True


def startMessenger():
    """Start the messenger session"""
    print("Starting a requests-session")
    global authSession
    global session
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
