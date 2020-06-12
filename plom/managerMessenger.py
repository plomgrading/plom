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

from io import StringIO, BytesIO

from plom.plom_exceptions import *
from plom.messenger import BaseMessenger

# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# TODO:
# _userName = "manager"


class ManagerMessenger(BaseMessenger):
    """Management-related communications."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def TriggerPopulateDB(self, force=False):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/DEV/admin/populateDB".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token},
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

        return response.json()

    def notify_pdf_of_paper_produced(self, test_num):
        """Notify the server that we have produced the PDF for a paper.

        Args:
            test_num (int): the test number.

        Returns:
            None
        """
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/pdf_produced/{}".format(self.server, test_num),
                verify=False,
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 400:
                raise PlomAuthenticationException() from None
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomRangeException(
                    "Paper number {} is outside valid range".format(test_num)
                ) from None
            elif response.status_code == 409:
                raise PlomSeriousException(
                    "Paper number {} has already been produced".format(test_num)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

    def getGlobalPageVersionMap(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/DEV/admin/pageVersionMap".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token},
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

        #import pickle
        #return pickle.loads(response.json())
        # ^&#king JSON mucks up dict keys
        d = response.json()
        dd = {}
        for k, v in d.items():
            dd[int(k)] = {int(kk): vv for kk, vv in v.items()}
        return dd

    # TODO: copy pasted from class Messenger: can we dedupe?
    def IDreturnIDdTask(self, code, studentID, studentName):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/DEV/ID/tasks/{}".format(self.server, code),
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

    def RgetCompletions(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/completions".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token},
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

        return response.json()

    def RgetStatus(self, test):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/status/{}".format(self.server, test),
                verify=False,
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Could not find test {}.".format(test)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return response.json()

    def getScannedTests(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/scanned".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getIncompleteTests(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/incomplete".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

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

    def IDgetRandomImage(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/ID/randomImage".format(self.server),
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
            elif response.status_code == 410:
                raise PlomNoMoreException("Cannot find ID image.") from None
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

    def getProgress(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/progress".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "q": q, "v": v},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getQuestionUserProgress(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/questionUserProgress".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "q": q, "v": v},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getMarkHistogram(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/markHistogram".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "q": q, "v": v},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def replaceMissingTestPage(self, code, t, p, v):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/missingTestPage/{}".format(self.server, code),
                verify=False,
                json={
                    "user": self.user,
                    "token": self.token,
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
                ) from None
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def removeScannedPage(self, code, t, p, v):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/admin/scannedPage/{}".format(self.server, code),
                verify=False,
                json={
                    "user": self.user,
                    "token": self.token,
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
                ) from None
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getUnknownPageNames(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/unknownPageNames".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token,},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getDiscardNames(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/discardNames".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getCollidingPageNames(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/collidingPageNames".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getTPageImage(self, t, p, v):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/scannedTPage".format(self.server),
                verify=False,
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": t,
                    "page": p,
                    "version": v,
                },
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                return None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return image

    def getHWPageImage(self, t, q, o):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/scannedHWPage".format(self.server),
                verify=False,
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": t,
                    "question": q,
                    "order": o,
                },
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                return None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return image

    def getXPageImage(self, t, o):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/scannedXPage".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "test": t, "order": o,},
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                return None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return image

    def getUnknownImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/unknownImage".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "fileName": fname,},
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                return None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return image

    def getDiscardImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/discardImage".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "fileName": fname,},
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                return None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return image

    def getCollidingImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/collidingImage".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "fileName": fname,},
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                return None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return image

    def removeUnknownImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/admin/unknownImage".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "fileName": fname,},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                return False
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return True

    def removeCollidingImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/admin/collidingImage".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "fileName": fname,},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                return False
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return True

    def getQuestionImages(self, testNumber, questionNumber):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/questionImages".format(self.server),
                json={
                    "user": self.user,
                    "token": self.token,
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
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}/{}.".format(
                        testNumber, questionNumber
                    )
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return imageList

    def getTestImages(self, testNumber):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/testImages".format(self.server),
                json={"user": self.user, "token": self.token, "test": testNumber,},
                verify=False,
            )
            response.raise_for_status()
            # response is [image1, image2,... image.n]
            imageList = []
            for img in MultipartDecoder.from_response(response).parts:
                imageList.append(BytesIO(img.content).getvalue())

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.".format(testNumber)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return imageList

    def checkPage(self, testNumber, pageNumber):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/admin/checkPage".format(self.server),
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": testNumber,
                    "page": pageNumber,
                },
                verify=False,
            )
            response.raise_for_status()
            # either [version] or [version, image]
            vimg = MultipartDecoder.from_response(response).parts
            ver = int(vimg[0].content)
            if len(vimg) == 2:
                rval = [ver, BytesIO(vimg[1].content).getvalue()]
            else:
                rval = [ver, None]
            # response is [v, None] or [v, image1]
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.".format(testNumber)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return rval

    def unknownToTestPage(self, fname, test, page, theta):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/unknownToTestPage".format(self.server),
                json={
                    "user": self.user,
                    "token": self.token,
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
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find test/page {}.".format(tp)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return collisionTest  # "collision" if colliding page created.

    def unknownToExtraPage(self, fname, test, question, theta):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/unknownToExtraPage".format(self.server),
                json={
                    "user": self.user,
                    "token": self.token,
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
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find test/question {}/{}.".format(test, question)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

    def collidingToTestPage(self, fname, test, page, version):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/collidingToTestPage".format(self.server),
                json={
                    "user": self.user,
                    "token": self.token,
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
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find test/page {}/{}.".format(test, page)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

    def discardToUnknown(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/discardToUnknown".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "fileName": fname,},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                return False
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return True

    def IDdeletePredictions(self):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/ID/predictedID".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token,},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def IDrunPredictions(self, rectangle, fileNumber, ignoreTimeStamp):
        self.SRmutex.acquire()
        try:
            response = self.session.post(
                "https://{}/ID/predictedID".format(self.server),
                verify=False,
                json={
                    "user": self.user,
                    "token": self.token,
                    "rectangle": rectangle,
                    "fileNumber": fileNumber,
                    "ignoreStamp": ignoreTimeStamp,
                },
            )
            response.raise_for_status()
            if response.status_code == 202:
                return [True, False]
            if response.status_code == 205:
                return [False, response.text]

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return [True, True]

    def getIdentified(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/identified".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token,},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getUserList(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/userList".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token,},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getUserDetails(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/userDetails".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token,},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getMarkReview(self, filterQ, filterV, filterU):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/markReview".format(self.server),
                verify=False,
                json={
                    "user": self.user,
                    "token": self.token,
                    "filterQ": filterQ,
                    "filterV": filterV,
                    "filterU": filterU,
                },
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getIDReview(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/idReview".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token,},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def getTOTReview(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/totReview".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token,},
            )
            response.raise_for_status()
            rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval

    def RgetAnnotatedImage(self, testNumber, questionNumber, version):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/annotatedImage".format(self.server),
                json={
                    "user": self.user,
                    "token": self.token,
                    "testNumber": testNumber,
                    "questionNumber": questionNumber,
                    "version": version,
                },
                verify=False,
            )
            response.raise_for_status()
            img = BytesIO(response.content).getvalue()

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.{}.{}".format(
                        testNumber, questionNumber, version
                    )
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return img

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

    def clearAuthorisationUser(self, someuser):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/authorisation/{}".format(self.server, someuser),
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

    def setUserEnable(self, someuser, enableFlag):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/enableDisable/{}".format(self.server, someuser),
                json={"user": self.user, "token": self.token, "enableFlag": enableFlag},
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

    def createModifyUser(self, someuser, password):
        self.SRmutex.acquire()
        try:
            response = self.session.post(
                "https://{}/authorisation/{}".format(self.server, someuser),
                json={"user": self.user, "token": self.token, "password": password},
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 406:
                return [False, response.text]
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        if response.status_code == 201:
            return [True, "User created."]
        elif response.status_code == 202:
            return [True, "User password updated"]

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

    def MreviewQuestion(self, testNumber, questionNumber, version):
        self.SRmutex.acquire()
        try:
            response = self.session.patch(
                "https://{}/MK/review".format(self.server),
                verify=False,
                json={
                    "user": self.user,
                    "token": self.token,
                    "testNumber": testNumber,
                    "questionNumber": questionNumber,
                    "version": version,
                },
            )
            response.raise_for_status()
            # rval = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Could not find t/q/v = {}/{}/{}.".format(
                        testNumber, questionNumber, version
                    )
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

    def IDreviewID(self, testNumber):
        self.SRmutex.acquire()
        try:
            response = self.session.patch(
                "https://{}/ID/review".format(self.server),
                verify=False,
                json={
                    "user": self.user,
                    "token": self.token,
                    "testNumber": testNumber,
                },
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Could not find test = {}.".format(testNumber)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

    def RgetOutToDo(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/outToDo".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token},
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

        return response.json()

    def RgetMarked(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/marked".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token, "q": q, "v": v},
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

        return response.json()
