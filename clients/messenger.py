# -*- coding: utf-8 -*-

"""
Backend bits n bobs to talk to the server
"""

__author__ = "Andrew Rechnitzer, Colin B. Macdonald"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer, Colin B. Macdonald"
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
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return True


# ----------------------
# ----------------------
# Test information
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


# ------------------------
# ------------------------
# ID client API stuff


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
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return progress


def IDaskNextTask():
    """Return the TGV of a paper that needs IDing.

    Return:
        string or None if no papers need IDing.

    Raises:
        SeriousError: if something has unexpectedly gone wrong.
    """
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
            return None
        tgv = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return tgv


def IDrequestClasslist():
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
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 404:
            raise PlomSeriousException("Server cannot find the class list") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return classlist


def IDrequestPredictions():
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
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Server cannot find the prediction list."
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return predictions


def IDrequestDoneTasks():
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
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return idList


def IDrequestImage(code):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/ID/images/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        imageList = []
        for img in MultipartDecoder.from_response(response).parts:
            imageList.append(
                BytesIO(img.content).getvalue()
            )  # pass back image as bytes
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Cannot find image file for {}.".format(code)
            ) from None
        elif response.status_code == 409:
            raise PlomSeriousException(
                "Another user has the image for {}. This should not happen".format(code)
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return imageList


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
            raise PlomBenignException("Task taken by another user.")
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

    imageList = []
    for img in MultipartDecoder.from_response(response).parts:
        imageList.append(BytesIO(img.content).getvalue())  # pass back image as bytes
    return imageList


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
        if response.status_code == 409:
            raise PlomBenignException(
                "Student number {} already in use".format(e)
            ) from None
        elif response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Another user has the image for {}. This should not happen".format(code)
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
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
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
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
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return maxMark


def TrequestDoneTasks():
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
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return idList


def TprogressCount():
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
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return progress


def TaskNextTask():
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/TOT/tasks/available".format(server, message_port),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        # throw errors when response code != 200.
        if response.status_code == 204:
            return None
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        progress = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return progress


def TclaimThisTask(task):
    SRmutex.acquire()
    try:
        response = session.patch(
            "https://{}:{}/TOT/tasks/{}".format(server, message_port, task),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        if response.status_code == 204:
            raise PlomBenignException("Task taken by another user.")
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()  # pass back image as bytes
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
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
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return True


def TrequestImage(testNumber):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/TOT/image/{}".format(server, message_port, testNumber),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        image = BytesIO(response.content).getvalue()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Cannot find image file for {}.".format(code)
            ) from None
        elif response.status_code == 409:
            raise PlomSeriousException(
                "Another user has the image for {}. This should not happen".format(code)
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
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
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Another user has the image for {}. This should not happen".format(code)
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    # TODO - do we need this return value?
    return True


# ------------------------
# ------------------------
# Marker stuff
def MgetMaxMark(question, version):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/maxMark".format(server, message_port),
            json={"user": _userName, "token": _token, "q": question, "v": version},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        maxMark = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 416:
            raise PlomSeriousException(response.text) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
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
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return True


def MrequestDoneTasks(q, v):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/tasks/complete".format(server, message_port),
            json={"user": _userName, "token": _token, "q": q, "v": v},
            verify=False,
        )
        response.raise_for_status()
        mList = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return mList


def MprogressCount(q, v):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/progress".format(server, message_port),
            json={"user": _userName, "token": _token, "q": q, "v": v},
            verify=False,
        )
        # throw errors when response code != 200.
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        progress = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return progress


def MaskNextTask(q, v):
    """Ask server for a new marking task, return tgv or None.

    None indicated no more tasks available.
    TODO: why are we using json for a string return?
    """

    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/tasks/available".format(server, message_port),
            json={"user": _userName, "token": _token, "q": q, "v": v},
            verify=False,
        )
        # throw errors when response code != 200.
        if response.status_code == 204:
            return None
        response.raise_for_status()
        # convert the content of the response to a textfile for identifier
        tgv = response.json()
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return tgv


def MrevertTask(code):
    SRmutex.acquire()
    try:
        response = session.patch(
            "https://{}:{}/MK/revert/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()
        if response.status_code == 204:
            raise PlomBenignException("No action to be taken.")

    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()


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
            raise PlomBenignException("Task taken by another user.")

    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    # should be multipart = [tags, image1, image2, ....]
    tags = "tagsAndImages[0].text  # this is raw text"
    imageList = []
    i = 0
    for img in MultipartDecoder.from_response(response).parts:
        if i == 0:
            tags = img.text
        else:
            imageList.append(
                BytesIO(img.content).getvalue()
            )  # pass back image as bytes
        i += 1
    return imageList, tags


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
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 406:
            raise PlomLatexException(
                "There is an error in your latex fragment"
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return image


def MrequestImages(code):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/images/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()

        # response is either [n, image1,..,image.n] or [n, image1,...,image.n, annotatedImage, plom-data]
        imagesAnnotAndPlom = MultipartDecoder.from_response(response).parts
        n = int(imagesAnnotAndPlom[0].content)  # 'n' sent as string
        imageList = [
            BytesIO(imagesAnnotAndPlom[i].content).getvalue() for i in range(1, n + 1)
        ]
        if len(imagesAnnotAndPlom) == n + 1:
            # all is fine - no annotated image or plom data
            anImage = None
            plDat = None
        elif len(imagesAnnotAndPlom) == n + 3:
            # all fine - last two parts are annotated image + plom-data
            anImage = BytesIO(
                imagesAnnotAndPlom[n + 1].content
            ).getvalue()  # pass back annotated-image as bytes
            plDat = BytesIO(
                imagesAnnotAndPlom[n + 2].content
            ).getvalue()  # pass back plomData as bytes
        else:
            raise PlomSeriousException(
                "Number of images passed doesn't make sense {} vs {}".format(
                    n, len(imagesAnnotAndPlom)
                )
            )
    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 404:
            raise PlomSeriousException(
                "Cannot find image file for {}.".format(code)
            ) from None
        elif response.status_code == 409:
            raise PlomSeriousException(
                "Another user has the image for {}. This should not happen".format(code)
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return [imageList, anImage, plDat]


def MrequestOriginalImages(task):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/originalImages/{}".format(server, message_port, task),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        if response.status_code == 204:
            raise PlomNoMoreException("No task = {}.".format(task))
        response.raise_for_status()
        # response is [image1, image2,... image.n]
        imageList = []
        for img in MultipartDecoder.from_response(response).parts:
            imageList.append(BytesIO(img.content).getvalue())

    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 404:
            raise PlomNoMoreException(
                "Cannot find image file for {}.{}.".format(testNumber, pageGroup)
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return imageList


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
            "md5sum": hashlib.md5(open(aname, "rb").read()).hexdigest(),
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
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 400:
            raise PlomSeriousException(
                "Image file is corrupted. This should not happen".format(code)
            ) from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
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
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 409:
            raise PlomBenignException("Task taken by another user.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()


def MrequestWholePaper(code):
    SRmutex.acquire()
    try:
        response = session.get(
            "https://{}:{}/MK/whole/{}".format(server, message_port, code),
            json={"user": _userName, "token": _token},
            verify=False,
        )
        response.raise_for_status()

        # response should be multipart = [[pageNames], f1,f2,f3..]
        imagesAsBytes = MultipartDecoder.from_response(response).parts
        images = []
        i = 0
        for iab in imagesAsBytes:
            if i == 0:
                pageNames = json.loads(iab.content)
            else:
                images.append(
                    BytesIO(iab.content).getvalue()
                )  # pass back image as bytes
            i += 1

    except requests.HTTPError as e:
        if response.status_code == 401:
            raise PlomSeriousException("You are not authenticated.") from None
        elif response.status_code == 409:
            raise PlomBenignException("Task taken by another user.") from None
        else:
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
    finally:
        SRmutex.release()

    return [pageNames, images]


# ------------------------
# ------------------------

session = None


def startMessenger():
    """Start the messenger session"""
    global session
    if session:
        print("Messenger: already have an requests-session")
    else:
        print("Messenger: starting a new requests-session")
        session = requests.Session()
        # TODO - UBC wifi is crappy: have some sort of "hey you've retried
        # nn times already, are you sure you want to keep retrying" message.
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
    try:
        response = session.get(
            "https://{}:{}/Version".format(server, message_port), verify=False,
        )
        response.raise_for_status()
    except requests.ConnectionError as err:
        raise PlomBenignException(
            "Cannot connect to server. Please check server details."
        ) from None
    r = response.text
    return r


def stopMessenger():
    """Stop the messenger"""
    global session
    if session:
        print("Messenger: stopping requests-session")
        session.close()
        session = None
