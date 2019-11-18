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
from requests_toolbelt import MultipartEncoder, MultipartDecoder
import json
import ssl
from PyQt5.QtWidgets import QMessageBox
import urllib3
from useful_classes import ErrorMessage
import time
import threading

from io import StringIO, BytesIO, TextIOWrapper
import plom_exceptions
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


def setServerDetails(s, mp):
    """Set the server IP and port"""
    global server, message_port
    server = s
    message_port = mp


def whoami():
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
            raise plom_exceptions.BenignException("You are not authenticated.")
        elif response.status_code == 400:  # API error
            raise plom_exceptions.PlomAPIException(response.json())
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    except requests.ConnectionError as err:
        raise plom_exceptions.SeriousError(
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
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return True


# ------------------------
# ------------------------
# ID client API stuff


def IDGetProgressCount():
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
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/ID/tasks/available".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        if response.status_code == 204:
            raise PlomNoMoreException("No tasks left.")
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


def IDGetClasslist():
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
        if response.status_code == 204:
            raise plom_exceptions.BenignException("Task taken by another user.")
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()  # pass back image as bytes
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
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

    # TODO - do we need this return value?
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
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/TOT/tasks/available".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        # throw errors when response code != 200.
        if response.status_code == 204:
            raise PlomNoMoreException("No tasks left.")
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


def TclaimThisTask(code):
    SRmutex.acquire()
    try:
        response = session.patch(
            "https://{}:{}/TOT/tasks/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        if response.status_code == 204:
            raise plom_exceptions.BenignException("Task taken by another user.")
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()  # pass back image as bytes
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
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


def TgetGroupImage(code):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/TOT/images/{}".format(server, message_port, code),
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


def TreturnTotaledTask(code, mark):
    SRmutex.acquire()
    try:
        response = session.put(
            "https://{}:{}/TOT/tasks/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token, "mark": mark},
            verify=False,
        )
        response.raise_for_status()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 404:
            raise plom_exceptions.SeriousError(
                "Another user has the image for {}. This should not happen".format(code)
            )
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    # TODO - do we need this return value?
    return True


# ------------------------
# ------------------------
# Marker stuff
def MgetMaxMark(pageGroup, version):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/maxMark".format(server, message_port),
            json={"user": _userName, "token": _token, "pg": pageGroup, "v": version},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        maxMark = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 416:
            raise plom_exceptions.SeriousError(response.text)
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return maxMark


def MdidNotFinishTask(code):
    SRmutex.acquire()
    try:
        response = session.delete(
            "https://{}:{}/MK/tasks/{}".format(server, message_port, code),
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


def MgetMarkedList(pg, v):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/tasks/complete".format(server, message_port),
            json={"user": _userName, "token": _token, "pg": pg, "v": v},
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


def MGetProgressCount(pg, v):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/progress".format(server, message_port),
            json={"user": _userName, "token": _token, "pg": pg, "v": v},
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


def MgetAvailable(pg, v):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/tasks/available".format(server, message_port),
            json={"user": _userName, "token": _token, "pg": pg, "v": v},
            verify=False,
        )
        # throw errors when response code != 200.
        if response.status_code == 204:
            raise PlomNoMoreException("No tasks left.")
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


def MclaimThisTask(code):
    SRmutex.acquire()
    try:
        response = session.patch(
            "https://{}:{}/MK/tasks/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        if response.status_code == 204:
            raise plom_exceptions.BenignException("Task taken by another user.")

        # response should be multipart = [image, tags]
        imageAndTags = MultipartDecoder.from_response(response).parts
        image = BytesIO(imageAndTags[0].content).getvalue()  # pass back image as bytes
        tags = imageAndTags[1].text
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return image, tags


def MlatexFragment(latex):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/latex".format(server, message_port),
            json={"user": _userName, "token": _token, "fragment": latex},
            verify=False,
        )
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 406:
            raise plom_exceptions.BenignException(
                "There is an error in your latex fragment"
            )
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return image


def MgetGroupImage(code):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/images/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()

        # response is either [image] or [image, annotatedImage, plom-data]
        imageAnImageAndPlom = MultipartDecoder.from_response(response).parts
        image = BytesIO(
            imageAnImageAndPlom[0].content
        ).getvalue()  # pass back image as bytes
        if len(imageAnImageAndPlom) == 3:
            anImage = BytesIO(
                imageAnImageAndPlom[1].content
            ).getvalue()  # pass back annotated-image as bytes
            plDat = BytesIO(
                imageAnImageAndPlom[2].content
            ).getvalue()  # pass back plomData as bytes

        else:
            anImage = None
            plDat = None

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

    return [image, anImage, plDat]


def MgetOriginalGroupImage(code):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/originalImage/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        if response.status_code == 204:
            raise PlomNoMoreException("No paper with code {}.".format(code))
        response.raise_for_status()
        # response is either [image] or [image, annotatedImage, plom-data]
        image = BytesIO(response.content).getvalue()  # pass back image as bytes

    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 404:
            raise plom_exceptions.SeriousError(
                "Cannot find image file for {}.".format(code)
            )
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return image


def MreturnMarkedTask(code, pg, ver, score, mtime, tags, aname, pname, cname):
    SRmutex.acquire()
    try:
        # doesn't like ints, so covert ints to strings
        param = {
            "user": _userName,
            "token": _token,
            "pg": str(pg),
            "ver": str(ver),
            "score": str(score),
            "mtime": str(mtime),
            "tags": tags,
            "comments": open(cname, "r").read(),
        }

        dat = MultipartEncoder(
            fields={
                "param": json.dumps(param),
                "annotated": (aname, open(aname, "rb"), "image/png"),  # image
                "plom": (pname, open(pname, "rb"), "text/plain"),  # plom-file
            }
        )
        response = session.put(
            "https://{}:{}/MK/tasks/{}".format(server, message_port, code),
            data=dat,
            headers={"Content-Type": dat.content_type},
            verify=False,
        )
        response.raise_for_status()
        ret = response.json()  # this is [#done, #total]
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 400:
            raise plom_exceptions.SeriousError(
                "Image file is corrupted. This should not happen".format(code)
            )
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()
    return ret


# todo - work out URLs for the various operations a little more nicely.
def MsetTag(code, tags):
    SRmutex.acquire()
    try:
        response = session.patch(
            "https://{}:{}/MK/tags/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token, "tags": tags},
            verify=False,
        )
        response.raise_for_status()

    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 409:
            raise plom_exceptions.BenignException("Task taken by another user.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()


def MgetWholePaper(code):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/whole/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()

        # response should be multipart = [image, tags]
        imagesAsBytes = MultipartDecoder.from_response(response).parts
        images = []
        for iab in imagesAsBytes:
            images.append(BytesIO(iab.content).getvalue())  # pass back image as bytes
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise plom_exceptions.SeriousError("You are not authenticated.")
        elif response.status_code == 409:
            raise plom_exceptions.BenignException("Task taken by another user.")
        else:
            raise plom_exceptions.SeriousError("Some other sort of error {}".format(e))
    finally:
        SRmutex.release()

    return images


# ------------------------
# ------------------------

session = None


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
