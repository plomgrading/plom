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
import time
import threading
import hashlib
import logging

from io import StringIO, BytesIO
from plom.plom_exceptions import *
from plom import Plom_API_Version, Default_Port

log = logging.getLogger("messenger")
# requests_log = logging.getLogger("urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BaseMessenger(object):
    """Basic communication with a Plom Server.

    Handles authentication and other common tasks; subclasses can add
    other features.
    """

    def __init__(self, s=None, port=Default_Port):
        sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        sslContext.check_hostname = False
        # Server defaults
        self.session = None
        self.user = None
        self.token = None
        if s:
            server = s
        else:
            server = "127.0.0.1"
        self.server = "{}:{}".format(server, port)
        message_port = None  # REMOVE
        self.SRmutex = threading.Lock()
        # base = "https://{}:{}/".format(s, mp)

    def whoami(self):
        return self.user

    def start(self):
        """Start the messenger session"""
        if self.session:
            log.debug("already have an requests-session")
        else:
            log.debug("starting a new requests-session")
            self.session = requests.Session()
            # TODO - UBC wifi is crappy: have some sort of "hey you've retried
            # nn times already, are you sure you want to keep retrying" message.
            self.session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
        try:
            response = self.session.get(
                "https://{}/Version".format(self.server), verify=False,
            )
            response.raise_for_status()
        except requests.ConnectionError as err:
            raise PlomBenignException(
                "Cannot connect to server. Please check server details."
            ) from None
        r = response.text
        return r

    def stop(self):
        """Stop the messenger"""
        if self.session:
            log.debug("stopping requests-session")
            self.session.close()
            self.session = None

    def isStarted(self):
        return bool(self.session)

    # ------------------------
    # ------------------------
    # Authentication stuff

    def requestAndSaveToken(self, user, pw):
        """Get a authorisation token from the server.

        The token is then used to authenticate future transactions with the server.

        """
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/users/{}".format(self.server, user),
                json={"user": user, "pw": pw, "api": Plom_API_Version},
                verify=False,
                timeout=5,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # convert the content of the response to a textfile for identifier
            self.token = response.json()
            self.user = user
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException(response.json()) from None
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
                "Cannot connect to server\n {}\n Please check details before trying again.".format(
                    server
                )
            ) from None
        finally:
            self.SRmutex.release()

    def clearAuthorisation(self, user, pw):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/authorisation".format(self.server),
                json={"user": user, "password": pw},
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

    def closeUser(self):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/users/{}".format(self.server, self.user),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return True

    # ----------------------
    # ----------------------
    # Test information

    def getInfoShortName(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/info/shortName".format(self.server), verify=False
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
            self.SRmutex.release()

        return shortName

    def getInfoGeneral(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/info/general".format(self.server), verify=False,
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
            self.SRmutex.release()

        fields = (
            "testName",
            "numberOfTests",
            "numberOfPages",
            "numberOfQuestions",
            "numberOfVersions",
            "publicCode",
        )
        return dict(zip(fields, pv))


class Messenger(BaseMessenger):
    """Handle communication with a Plom Server."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ------------------------
    # ------------------------
    # ID client API stuff

    def IDprogressCount(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/ID/progress".format(self.server),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # convert the content of the response to a textfile for identifier
            progress = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return progress

    def IDaskNextTask(self):
        """Return the TGV of a paper that needs IDing.

        Return:
            string or None if no papers need IDing.

        Raises:
            SeriousError: if something has unexpectedly gone wrong.
        """
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/ID/tasks/available".format(self.server),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            if response.status_code == 204:
                return None
            tgv = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return tgv

    def IDrequestClasslist(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/ID/classlist".format(self.server),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # you can assign to the encoding to override the autodetection
            # TODO: define API such that classlist must be utf-8?
            # print(response.encoding)
            # response.encoding = 'utf-8'
            classlist = StringIO(response.text)
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Server cannot find the class list"
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return classlist

    def IDrequestPredictions(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/ID/predictions".format(self.server),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
            # TODO: print(response.encoding) autodetected
            predictions = StringIO(response.text)
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Server cannot find the prediction list."
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return predictions

    def IDrequestDoneTasks(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/ID/tasks/complete".format(self.server),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
            idList = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return idList

    def IDrequestImage(self, code):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/ID/images/{}".format(self.server, code),
                json={"user": self.user, "token": self.token},
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
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.".format(code)
                ) from None
            elif response.status_code == 409:
                raise PlomSeriousException(
                    "Another user has the image for {}. This should not happen".format(
                        code
                    )
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return imageList

    # ------------------------

    # TODO - API needs improve. Both of these throw a put/patch to same url = /ID/tasks/{tgv}
    # One only updates the user claim, while the other actually ID's it.
    # Think of better url structure for this?
    def IDclaimThisTask(self, code):
        self.SRmutex.acquire()
        try:
            response = self.session.patch(
                "https://{}/ID/tasks/{}".format(self.server, code),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            if response.status_code == 204:
                raise PlomTakenException("Task taken by another user.")
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        imageList = []
        for img in MultipartDecoder.from_response(response).parts:
            imageList.append(
                BytesIO(img.content).getvalue()
            )  # pass back image as bytes
        return imageList

    def IDreturnIDdTask(self, code, studentID, studentName):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/ID/tasks/{}".format(self.server, code),
                json={
                    "user": self.user,
                    "token": self.token,
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
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Another user has the image for {}. This should not happen".format(
                        code
                    )
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        # TODO - do we need this return value?
        return True

    def IDdidNotFinishTask(self, code):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/ID/tasks/{}".format(self.server, code),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return True

    # ------------------------
    # ------------------------
    # Totaller client API stuff

    def TgetMaxMark(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/TOT/maxMark".format(self.server),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # convert the content of the response to a textfile for identifier
            maxMark = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return maxMark

    def TrequestDoneTasks(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/TOT/tasks/complete".format(self.server),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
            idList = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return idList

    def TprogressCount(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/TOT/progress".format(self.server),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # convert the content of the response to a textfile for identifier
            progress = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return progress

    def TaskNextTask(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/TOT/tasks/available".format(self.server),
                json={"user": self.user, "token": self.token},
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
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return progress

    def TclaimThisTask(self, task):
        self.SRmutex.acquire()
        try:
            response = self.session.patch(
                "https://{}/TOT/tasks/{}".format(self.server, task),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            if response.status_code == 204:
                raise PlomTakenException("Task taken by another user.")
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()  # pass back image as bytes
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return image

    def TdidNotFinishTask(self, code):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/TOT/tasks/{}".format(self.server, code),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return True

    def TrequestImage(self, testNumber):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/TOT/image/{}".format(self.server, testNumber),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.".format(code)
                ) from None
            elif response.status_code == 409:
                raise PlomSeriousException(
                    "Another user has the image for {}. This should not happen".format(
                        code
                    )
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return image

    def TreturnTotaledTask(self, code, mark):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/TOT/tasks/{}".format(self.server, code),
                json={"user": self.user, "token": self.token, "mark": mark},
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Another user has the image for {}. This should not happen".format(
                        code
                    )
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        # TODO - do we need this return value?
        return True

    # ------------------------
    # ------------------------
    # Marker stuff
    def MgetMaxMark(self, question, ver):
        """Get the maximum mark for this question and version.

        Raises:
            PlomRangeExeception: `question` or `ver` is out of range.
            PlomAuthenticationException:
            PlomSeriousException: something unexpected happened.
        """
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/maxMark".format(self.server),
                json={"user": self.user, "token": self.token, "q": question, "v": ver},
                verify=False,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # convert the content of the response to a textfile for identifier
            maxMark = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 416:
                raise PlomRangeException(response.text) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return maxMark

    def MdidNotFinishTask(self, code):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/MK/tasks/{}".format(self.server, code),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return True

    def MrequestDoneTasks(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/tasks/complete".format(self.server),
                json={"user": self.user, "token": self.token, "q": q, "v": v},
                verify=False,
            )
            response.raise_for_status()
            mList = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return mList

    def MprogressCount(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/progress".format(self.server),
                json={"user": self.user, "token": self.token, "q": q, "v": v},
                verify=False,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # convert the content of the response to a textfile for identifier
            progress = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return progress

    def MaskNextTask(self, q, v):
        """Ask server for a new marking task, return tgv or None.

        None indicated no more tasks available.
        TODO: why are we using json for a string return?
        """

        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/tasks/available".format(self.server),
                json={"user": self.user, "token": self.token, "q": q, "v": v},
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
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return tgv

    def MrevertTask(self, code):
        self.SRmutex.acquire()
        try:
            response = self.session.patch(
                "https://{}/MK/revert/{}".format(self.server, code),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
            if response.status_code == 204:
                raise PlomBenignException("No action to be taken.")

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

    def MclaimThisTask(self, code):
        self.SRmutex.acquire()
        try:
            response = self.session.patch(
                "https://{}/MK/tasks/{}".format(self.server, code),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
            if response.status_code == 204:
                raise PlomTakenException("Task taken by another user.")

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

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

    def MlatexFragment(self, latex):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/latex".format(self.server),
                json={"user": self.user, "token": self.token, "fragment": latex},
                verify=False,
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 406:
                raise PlomLatexException(
                    "There is an error in your latex fragment"
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return image

    def MrequestImages(self, code):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/images/{}".format(self.server, code),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()

            # response is either [n, image1,..,image.n] or [n, image1,...,image.n, annotatedImage, plom-data]
            imagesAnnotAndPlom = MultipartDecoder.from_response(response).parts
            n = int(imagesAnnotAndPlom[0].content)  # 'n' sent as string
            imageList = [
                BytesIO(imagesAnnotAndPlom[i].content).getvalue()
                for i in range(1, n + 1)
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
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.".format(code)
                ) from None
            elif response.status_code == 409:
                raise PlomSeriousException(
                    "Another user has the image for {}. This should not happen".format(
                        code
                    )
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return [imageList, anImage, plDat]

    def MrequestOriginalImages(self, task):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/originalImages/{}".format(self.server, task),
                json={"user": self.user, "token": self.token},
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
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomNoMoreException(
                    "Cannot find image file for {}.{}.".format(testNumber, pageGroup)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return imageList

    def MreturnMarkedTask(self, code, pg, ver, score, mtime, tags, aname, pname, cname):
        self.SRmutex.acquire()
        try:
            # doesn't like ints, so covert ints to strings
            param = {
                "user": self.user,
                "token": self.token,
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
            response = self.session.put(
                "https://{}/MK/tasks/{}".format(self.server, code),
                data=dat,
                headers={"Content-Type": dat.content_type},
                verify=False,
            )
            response.raise_for_status()
            ret = response.json()  # this is [#done, #total]
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 400:
                raise PlomSeriousException(
                    "Image file is corrupted. This should not happen".format(code)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return ret

    # todo - work out URLs for the various operations a little more nicely.
    def MsetTag(self, code, tags):
        self.SRmutex.acquire()
        try:
            response = self.session.patch(
                "https://{}/MK/tags/{}".format(self.server, code),
                json={"user": self.user, "token": self.token, "tags": tags},
                verify=False,
            )
            response.raise_for_status()

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 409:
                raise PlomTakenException("Task taken by another user.") from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

    def MrequestWholePaper(self, code, questionNumber):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/whole/{}/{}".format(self.server, code, questionNumber),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()

            # response should be multipart = [ pageData, f1,f2,f3..]
            imagesAsBytes = MultipartDecoder.from_response(response).parts
            images = []
            i = 0
            for iab in imagesAsBytes:
                if i == 0:
                    pageData = json.loads(iab.content)
                else:
                    images.append(
                        BytesIO(iab.content).getvalue()
                    )  # pass back image as bytes
                i += 1

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 409:
                raise PlomTakenException("Task taken by another user.") from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return [pageData, images]

    def MshuffleImages(self, code, imageRefs):
        self.SRmutex.acquire()
        try:
            response = self.session.patch(
                "https://{}/MK/shuffle/{}".format(self.server, code),
                json={"user": self.user, "token": self.token, "imageRefs": imageRefs},
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

    # ------------------------
    # ------------------------


from .scanMessenger import ScanMessenger
from .finishMessenger import FinishMessenger
from .managerMessenger import ManagerMessenger
