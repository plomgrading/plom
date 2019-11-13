# -*- coding: utf-8 -*-

"""
Backend bits n bobs to talk to the server
"""

__author__ = "Andrew Rechnitzer, Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer, Colin B. Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald", "Elvis Cai", "Matt Coles"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
import asyncio
import requests
import easywebdav2
import json
import ssl
from PyQt5.QtWidgets import QMessageBox
import urllib3
from useful_classes import ErrorMessage
import time
import threading

from io import StringIO, BytesIO, TextIOWrapper
import plom_exceptions

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
webdav_port = 41985
SRmutex = threading.Lock()
_userName = None
_token = None


def setServerDetails(s, mp, dp):
    """Set the server IP, message port and webdav port"""
    global server, message_port, webdav_port
    server = s
    message_port = mp
    webdav_port = dp


def whoami():
    global _userName
    return _userName


def http_messaging(msg):
    try:
        response = session.put(
            "https://{}:{}/".format(server, message_port),
            json={"msg": msg},
            verify=False,
        )
    except:
        return [
            "ERR",
            "Something went seriously wrong. Check connection details and try again.",
        ]
    return response.json()["rmsg"]


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
        response = session.put(
            "https://{}:{}/users/{}".format(server, message_port, user),
            json={"user": user, "pw": pw, "api": Plom_API_Version},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        _token = response.json()
        _userName = user
    except requests.HTTPError as e:
        if response.status_code == 401:  # authentication error
            raise plom_exceptions.BenignException("You are not authenticated.")
        elif response.status_code == 400:  # API error
            raise plom_exceptions.PlomAPIException(response.json())
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
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
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return True


# ----------------


def msg(msgcode, *args):
    """Send message using https and get back return message.
    If error then pop-up an error message.
    """
    msg_ = (msgcode, _userName, _token, *args)
    SRmutex.acquire()
    try:
        rmsg = http_messaging(msg_)
    finally:
        SRmutex.release()

    if rmsg[0] == "ACK":
        return rmsg
    elif rmsg[0] == "ERR":
        ErrorMessage("Server says: " + rmsg[1]).exec_()
        return rmsg
    else:
        print(">>> Error I didn't expect. Return message was {}".format(rmsg))
        ErrorMessage("Something really wrong has happened.").exec_()


def msg_nopopup(msgcode, *args):
    """Send message using the asyncio message handler and get back
    return message.
    """
    msg = (msgcode, _userName, _token, *args)
    SRmutex.acquire()
    try:
        rmsg = http_messaging(msg)
    finally:
        SRmutex.release()

    if rmsg[0] in ("ACK", "ERR"):
        return rmsg
    else:
        raise RuntimeError(
            "Unexpected response from server.  Consider filing a bug?  The return from the server was:\n\n"
            + str(rmsg)
        )


def getFileDav(dfn, lfn):
    """Get file dfn from the webdav server and save as lfn."""
    webdav = easywebdav2.connect(
        server, port=webdav_port, protocol="https", verify_ssl=False
    )
    try:
        webdav.download(dfn, lfn)
    except Exception as ex:
        template = ">>> An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)


def putFileDav(lfn, dfn):
    """Upload file lfn to the webdav as dfn."""
    webdav = easywebdav2.connect(
        server, port=webdav_port, protocol="https", verify_ssl=False
    )
    try:
        webdav.upload(lfn, dfn)
    except Exception as ex:
        template = ">>> An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)


def getFileDav_woInsanity(dfn, lfn):
    """Get file dfn from the webdav server and save as lfn.

    Does not do anything for exceptions: that's the caller's problem.
    """
    webdav = easywebdav2.connect(
        server, port=webdav_port, protocol="https", verify_ssl=False
    )
    webdav.download(dfn, lfn)


def putFileDav_woInsanity(lfn, dfn):
    """Upload file lfn to the webdav as dfn.

    Does not do any exception handling: that's the caller's problem.
    """
    webdav = easywebdav2.connect(
        server, port=webdav_port, protocol="https", verify_ssl=False
    )
    webdav.upload(lfn, dfn)


# ------------------------
# ------------------------
# ID client API stuff


def IDGetProgressCount():
    global _userName, _token

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
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return progress


def IDGetAvailable():
    global _userName, _token

    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/ID/tasks/available".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        progress = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 204:
            raise plom_exceptions.BenignException("No tasks left.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return progress


def IDGetClasslist():
    global _userName, _token

    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/ID/classlist".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        classlist = TextIOWrapper(BytesIO(response.content))
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 404:
            raise plom_exceptions.SeriousError("Server cannot find the class list")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return classlist


def IDGetPredictions():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/ID/predictions".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        predictions = TextIOWrapper(BytesIO(response.content))
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 404:
            raise plom_exceptions.SeriousError(
                "Server cannot find the prediction list."
            )
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return predictions


def IDgetAlreadyComplete():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/ID/tasks/complete".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        idList = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return idList


def IDgetGroupImage(code):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/ID/images/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 404:
            raise plom_exceptions.SeriousError(
                "Cannot find image file for {}.".format(code)
            )
        elif response.status_code == 409:
            raise plom_exceptions.SeriousError(
                "Another user has the image for {}. This should not happen".format(code)
            )
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return image


# ------------------------

# TODO - API needs improve. Both of these throw a put/patch to same url = /ID/tasks/{tgv}
# One only updates the user claim, while the other actually ID's it.
# Think of better url structure for this?
def IDclaimThisTask(code):
    SRmutex.acquire()
    try:
        response = session.patch(
            "https://{}:{}/ID/tasks/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()  # pass back image as bytes
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 204:
            raise plom_exceptions.BenignException("Task taken by another user.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return image


def IDreturnIDdTask(code, studentID, studentName):
    SRmutex.acquire()
    try:
        response = session.put(
            "https://{}:{}/ID/tasks/{}".format(server, message_port, code),
            json={
                "user": _userName,
                "token": _token,
                "sid": studentID,
                "sname": studentName,
            },
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if resposne.status_code == 409:
            raise plom_exceptions.BenignException(
                "Student number {} already in use".format(e)
            )
        elif response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 404:
            raise plom_exceptions.SeriousError(
                "Another user has the image for {}. This should not happen".format(code)
            )
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return True


def IDdidNotFinishTask(code):
    SRmutex.acquire()
    try:
        response = session.delete(
            "https://{}:{}/ID/tasks/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return True


# ------------------------
# ------------------------
# Totaller client API stuff


def TgetMaxMark():
    global _userName, _token

    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/TOT/maxMark".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        maxMark = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return maxMark


def TgetAlreadyComplete():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/TOT/tasks/complete".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        idList = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return idList


def TGetProgressCount():
    global _userName, _token

    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/TOT/progress".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        progress = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return progress


def TGetAvailable():
    global _userName, _token

    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/TOT/tasks/available".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        progress = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 204:
            raise plom_exceptions.BenignException("No tasks left.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return progress


def TclaimThisTask(code):
    SRmutex.acquire()
    try:
        response = session.patch(
            "https://{}:{}/TOT/tasks/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()  # pass back image as bytes
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 204:
            raise plom_exceptions.BenignException("Task taken by another user.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return image


def TdidNotFinishTask(code):
    SRmutex.acquire()
    try:
        response = session.delete(
            "https://{}:{}/TOT/tasks/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return True


# ------------------------
# ------------------------

session = None


def startMessenger():
    """Start the messenger session"""
    print("Starting a requests-session")
    global session
    session = requests.Session()
    # set max_retries to large number because UBC-wifi is pretty crappy.
    # TODO - set smaller number and have some sort of "hey you've retried
    # nn times already, are you sure you want to keep retrying" message.
    session.mount("https://", requests.adapters.HTTPAdapter(max_retries=50))


def stopMessenger():
    """Stop the messenger"""
    print("Stopped messenger session")
    session.close()
