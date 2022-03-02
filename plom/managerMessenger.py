# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

import hashlib
from io import StringIO, BytesIO
import json

import requests
from requests_toolbelt import MultipartDecoder, MultipartEncoder

from plom import undo_json_packing_of_version_map
from plom.plom_exceptions import PlomBenignException, PlomSeriousException
from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomConflict,
    PlomExistingDatabase,
    PlomNoMoreException,
    PlomOwnersLoggedInException,
    PlomServerNotReady,
    PlomRangeException,
    PlomTakenException,
    PlomUnidentifiedPaperException,
)
from plom.baseMessenger import BaseMessenger


# TODO:
# _userName = "manager"


class ManagerMessenger(BaseMessenger):
    """Management-related communications."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def TriggerPopulateDB(self, version_map={}):
        """Instruct the server to generate paper data in the database.

        Returns:
            str: a big block of largely useless status or summary info
                from the database commands.

        Raises:
            PlomExistingDatabase: already has a populated database.
            PlomServerNotReady: e.g., has no spec.
            PlomAuthenticationException: login troubles.
            PlomSeriousException: unexpected errors.

        TODO: currently this call can take quite a long time (for a
        large number of papers).  Timeout set longer as a workaround.
        See Issue #1929 for a future proper fix.
        """
        self.SRmutex.acquire()
        try:
            # increase the timeout, see docs above
            timeout = (self.default_timeout[0], 3 * self.default_timeout[1])
            response = self.put(
                "/admin/populateDB",
                json={
                    "user": self.user,
                    "token": self.token,
                    "version_map": version_map,
                },
                timeout=timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 403:
                raise PlomAuthenticationException(response.reason) from None
            if response.status_code == 409:
                raise PlomExistingDatabase(response.reason) from None
            if response.status_code == 400:
                raise PlomServerNotReady(response.reason) from None
            raise PlomSeriousException("Unexpected {}".format(e)) from None
        finally:
            self.SRmutex.release()

        return response.text

    def getGlobalPageVersionMap(self):
        with self.SRmutex:
            try:
                response = self.get(
                    "/admin/pageVersionMap",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                elif response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None
        # JSON casts dict keys to str, force back to ints
        return undo_json_packing_of_version_map(response.json())

    # TODO: copy pasted from Messenger.IDreturnIDdTask: can we dedupe?
    def id_paper(self, code, studentID, studentName):
        """Identify a paper directly, not as part of a IDing task.

        Exceptions:
            PlomConflict: `studentID` already used on a different paper.
            PlomAuthenticationException: login problems.
            PlomSeriousException: other errors.
        """
        self.SRmutex.acquire()
        try:
            response = self.put(
                f"/ID/{code}",
                json={
                    "user": self.user,
                    "token": self.token,
                    "sid": studentID,
                    "sname": studentName,
                },
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 409:
                raise PlomConflict(e) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                raise PlomSeriousException(e) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def un_id_paper(self, code):
        """Remove the identify of a paper directly.

        TODO: eventually this may want its own API call.

        Exceptions:
            PlomAuthenticationException: login problems.
            PlomSeriousException: other errors.
        """
        with self.SRmutex:
            try:
                response = self.put(
                    f"/ID/{code}",
                    json={
                        "user": self.user,
                        "token": self.token,
                        "sid": "",
                        "sname": "",
                    },
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 404:
                    raise PlomSeriousException(e) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def upload_classlist(self, classdict):
        """Give the server a classlist.

        Args:
            classdict (list): list of dict.  Each dict is one student.
                It MUST have keys `"id"` and `"studentNumber"` (case
                matters).  There may be other keys included as well.
                Keys should probably be homogeneous between rows (TODO?).

        Exceptions:
            PlomConflict: server already has one.
            PlomRangeException: this classlist causes an invalid server
                spec.  Most likely numberToProduce is too small but
                check error message to be sure.
            PlomAuthenticationException: login problems.
            PlomServerNotReady: e.g., it has no spec.
            PlomSeriousException: other errors.
        """
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/ID/classlist",
                json={
                    "user": self.user,
                    "token": self.token,
                    "classlist": classdict,
                },
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 409:
                raise PlomConflict(e) from None
            if response.status_code == 400 and "no spec" in response.reason:
                raise PlomServerNotReady(response.reason) from None
            if response.status_code == 406:
                raise PlomRangeException(e) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 403:
                raise PlomAuthenticationException(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def upload_spec(self, specdata):
        """Give the server a specification.

        Args:
            specdata (dict): see :func:`plom.SpecVerifier`.

        Exceptions:
            PlomConflict: server already has a database, cannot accept spec.
            PlomAuthenticationException: login problems.
            PlomSeriousException: other errors.

        Returns:
            None
        """
        with self.SRmutex:
            try:
                response = self.put(
                    "/info/spec",
                    json={
                        "user": self.user,
                        "token": self.token,
                        "spec": specdata,
                    },
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 403:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 400:
                    raise PlomSeriousException(response.reason) from None
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def RgetCompletionStatus(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/completionStatus",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return response.json()

    def RgetStatus(self, test):
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/REP/status/{test}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                raise PlomSeriousException(f"Could not find test {test}.") from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return response.json()

    def getScannedTests(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/scanned",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getIncompleteTests(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/incomplete",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def RgetDanglingPages(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/dangling",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def IDprogressCount(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/ID/progress",
                json={"user": self.user, "token": self.token},
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # convert the content of the response to a textfile for identifier
            progress = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return progress

    def IDgetImageList(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/TMP/imageList",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            # TODO: print(response.encoding) autodetected
            imageList = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return imageList

    def IDrequestPredictions(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/ID/predictions",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            # TODO: print(response.encoding) autodetected
            predictions = StringIO(response.text)
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server cannot find the prediction list."
                ) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return predictions

    def IDgetImageFromATest(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/ID/randomImage",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            imageList = []
            for img in MultipartDecoder.from_response(response).parts:
                imageList.append(
                    BytesIO(img.content).getvalue()
                )  # pass back image as bytes
            return imageList
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 410:
                raise PlomNoMoreException("Cannot find ID image.") from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getProgress(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/progress",
                json={"user": self.user, "token": self.token, "q": q, "v": v},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getQuestionUserProgress(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/questionUserProgress",
                json={"user": self.user, "token": self.token, "q": q, "v": v},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getMarkHistogram(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/markHistogram",
                json={"user": self.user, "token": self.token, "q": q, "v": v},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def replaceMissingTestPage(self, t, p, v):
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/admin/missingTestPage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": t,
                    "page": p,
                    "version": v,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the page - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 409:
                raise PlomOwnersLoggedInException(response.json()) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def replaceMissingDNMPage(self, t, p):
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/admin/missingDNMPage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": t,
                    "page": p,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the page - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 409:
                raise PlomOwnersLoggedInException(response.json()) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def replaceMissingIDPage(self, t):
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/admin/missingIDPage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": t,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the page - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 409:
                raise PlomOwnersLoggedInException(response.json()) from None
            if response.status_code == 410:
                raise PlomUnidentifiedPaperException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def replaceMissingHWQuestion(self, student_id=None, test=None, question=None):
        # can replace by SID or by test-number
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/admin/missingHWQuestion",
                json={
                    "user": self.user,
                    "token": self.token,
                    "question": question,
                    "sid": student_id,
                    "test": test,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the TPV - this should not happen!"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 405:  # that question already has pages
                raise PlomTakenException() from None
            if response.status_code == 409:
                raise PlomOwnersLoggedInException(response.json()) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def removeSinglePage(self, test_number, page_name):
        self.SRmutex.acquire()
        try:
            response = self.delete(
                "/admin/singlePage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": test_number,
                    "page_name": page_name,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 410:
                raise PlomSeriousException(
                    "Server could not find the page - this should not happen!"
                ) from None
            if response.status_code == 409:
                raise PlomOwnersLoggedInException(response.json()) from None
            if response.status_code == 406:
                raise PlomSeriousException(
                    f"Page name '{page_name}' is invalid"
                ) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def removeAllScannedPages(self, test_number):
        self.SRmutex.acquire()
        try:
            response = self.delete(
                "/admin/scannedPages",
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": test_number,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the page - this should not happen!"
                ) from None
            if response.status_code == 409:
                raise PlomOwnersLoggedInException(response.json()) from None
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getUnknownPageNames(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/unknownPageNames",
                json={
                    "user": self.user,
                    "token": self.token,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getDiscardNames(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/discardNames",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getCollidingPageNames(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/collidingPageNames",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getTPageImage(self, t, p, v):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/scannedTPage",
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
            return image
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                return None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getHWPageImage(self, t, q, o):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/scannedHWPage",
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
            return image
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                return None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getEXPageImage(self, t, q, o):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/scannedEXPage",
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
            return image
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                return None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getUnknownImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/unknownImage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                },
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
            return image
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                return None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getDiscardImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/discardImage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                },
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
            return image
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                return None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getCollidingImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/collidingImage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                },
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
            return image
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                return None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def removeUnknownImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.delete(
                "/admin/unknownImage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                },
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                return False
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()
        return True

    def removeCollidingImage(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.delete(
                "/admin/collidingImage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                },
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                return False
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()
        return True

    def getQuestionImages(self, testNumber, questionNumber):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/questionImages",
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": testNumber,
                    "question": questionNumber,
                },
            )
            response.raise_for_status()
            # response is [n, image1, image2,... image.n]
            imageList = []
            i = -1  # we skip the first part
            for img in MultipartDecoder.from_response(response).parts:
                i += 1
                if i == 0:
                    continue
                imageList.append(BytesIO(img.content).getvalue())
            return imageList

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                raise PlomSeriousException(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getTestImages(self, testNumber):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/testImages",
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": testNumber,
                },
            )
            response.raise_for_status()
            # response is [n, image1, image2,... image.n]
            imageList = []
            i = -1  # we skip the first part
            for img in MultipartDecoder.from_response(response).parts:
                i += 1
                if i == 0:
                    continue
                imageList.append(BytesIO(img.content).getvalue())
            return imageList

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                raise PlomSeriousException(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def checkTPage(self, testNumber, pageNumber):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/checkTPage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "test": testNumber,
                    "page": pageNumber,
                },
            )
            response.raise_for_status()
            # either ["scanned", version] or ["collision", version, image]
            vimg = MultipartDecoder.from_response(response).parts
            ver = int(vimg[1].content)
            if len(vimg) == 3:  # just look at length - sufficient for now?
                rval = [ver, BytesIO(vimg[2].content).getvalue()]
            else:
                rval = [ver, None]
            return rval  # [v, None] or [v, image1]
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.".format(testNumber)
                ) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def unknownToTestPage(self, fname, test, page, theta):
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/admin/unknownToTestPage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                    "test": test,
                    "page": page,
                    "rotation": theta,
                },
            )
            response.raise_for_status()
            collisionTest = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 403:
                raise PlomAuthenticationException(response.reason) from None
            if response.status_code == 406:
                raise PlomOwnersLoggedInException(response.reason) from None
            if response.status_code == 409:
                raise PlomConflict(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return collisionTest  # "collision" if colliding page created.

    def unknownToExtraPage(self, fname, test, questions, theta):
        # TODO: uncomment for very questionable testing
        # questions.append(3)
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/admin/unknownToExtraPage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                    "test": test,
                    "questions": questions,
                    "rotation": theta,
                },
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 403:
                raise PlomAuthenticationException(response.reason) from None
            if response.status_code == 406:
                raise PlomOwnersLoggedInException(response.reason) from None
            if response.status_code == 409:
                raise PlomConflict(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def unknownToHWPage(self, fname, test, questions, theta):
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/admin/unknownToHWPage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                    "test": test,
                    "questions": questions,
                    "rotation": theta,
                },
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 403:
                raise PlomAuthenticationException(response.reason) from None
            if response.status_code == 406:
                raise PlomOwnersLoggedInException(response.reason) from None
            if response.status_code == 409:
                raise PlomConflict(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def collidingToTestPage(self, fname, test, page, version):
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/admin/collidingToTestPage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                    "test": test,
                    "page": page,
                    "version": version,
                },
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 403:
                raise PlomAuthenticationException(response.reason) from None
            if response.status_code == 406:
                raise PlomOwnersLoggedInException(response.reason) from None
            if response.status_code == 409:
                raise PlomConflict(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def discardToUnknown(self, fname):
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/admin/discardToUnknown",
                json={
                    "user": self.user,
                    "token": self.token,
                    "fileName": fname,
                },
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                return False
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()
        return True

    def IDdeletePredictions(self):
        self.SRmutex.acquire()
        try:
            response = self.delete(
                "/ID/predictedID",
                json={
                    "user": self.user,
                    "token": self.token,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def IDputPredictions(self, predictions):
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/ID/predictions",
                json={
                    "user": self.user,
                    "token": self.token,
                    "predictions": predictions,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def IDrunPredictions(self, rectangle, fileNumber, ignoreTimeStamp):
        self.SRmutex.acquire()
        try:
            response = self.post(
                "/ID/predictedID",
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
            return [True, True]
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getIdentified(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/identified",
                json={
                    "user": self.user,
                    "token": self.token,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getNotAutoIdentified(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/notautoid",
                json={
                    "user": self.user,
                    "token": self.token,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getUserList(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/userList",
                json={
                    "user": self.user,
                    "token": self.token,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getUserDetails(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/userDetails",
                json={
                    "user": self.user,
                    "token": self.token,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getMarkReview(self, filterQ, filterV, filterU, filterM=True):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/markReview",
                json={
                    "user": self.user,
                    "token": self.token,
                    "filterQ": filterQ,
                    "filterV": filterV,
                    "filterU": filterU,
                    "filterM": filterM,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getIDReview(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/idReview",
                json={
                    "user": self.user,
                    "token": self.token,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def clearAuthorisationUser(self, someuser):
        self.SRmutex.acquire()
        try:
            response = self.delete(
                f"/authorisation/{someuser}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def enableUser(self, someuser):
        self.SRmutex.acquire()
        try:
            response = self.put(
                f"/enable/{someuser}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 403:
                raise PlomAuthenticationException(response.reason) from None
            if response.status_code == 400:
                raise PlomConflict(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def disableUser(self, someuser):
        self.SRmutex.acquire()
        try:
            response = self.put(
                f"/disable/{someuser}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 403:
                raise PlomAuthenticationException(response.reason) from None
            if response.status_code == 400:
                raise PlomConflict(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def createModifyUser(self, someuser, password):
        self.SRmutex.acquire()
        try:
            response = self.post(
                f"/authorisation/{someuser}",
                json={"user": self.user, "token": self.token, "password": password},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 406:
                return [False, response.text]
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()
        if response.status_code == 201:
            return [True, "User created."]
        if response.status_code == 202:
            return [True, "User password updated"]
        raise PlomSeriousException(f"Unexpected {response.status_code}") from None

    def MrevertTask(self, code):
        self.SRmutex.acquire()
        try:
            response = self.patch(
                f"/MK/revert/{code}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            if response.status_code == 204:
                raise PlomBenignException("No action to be taken.")

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def MreviewQuestion(self, testNumber, questionNumber, version):
        self.SRmutex.acquire()
        try:
            response = self.patch(
                "/MK/review",
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
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Could not find t/q/v = {}/{}/{}.".format(
                        testNumber, questionNumber, version
                    )
                ) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def IDreviewID(self, testNumber):
        self.SRmutex.acquire()
        try:
            response = self.patch(
                "/ID/review",
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
            if response.status_code == 404:
                raise PlomSeriousException(
                    f"Could not find test {testNumber}."
                ) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def RgetOutToDo(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/outToDo",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return response.json()

    def RgetMarked(self, q, v):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/marked",
                json={"user": self.user, "token": self.token, "q": q, "v": v},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return response.json()

    def putSolutionImage(self, question, version, fileName):
        with self.SRmutex:
            try:
                with open(fileName, "rb") as fh:
                    param = {
                        "user": self.user,
                        "token": self.token,
                        "question": question,
                        "version": version,
                        "md5sum": hashlib.md5(fh.read()).hexdigest(),
                    }
                    # reset stream position to start before reading again
                    fh.seek(0)
                    dat = MultipartEncoder(
                        fields={
                            "param": json.dumps(param),
                            "image": fh,
                        }
                    )
                    response = self.put(
                        "/admin/solution",
                        json={"user": self.user, "token": self.token},
                        data=dat,
                        headers={"Content-Type": dat.content_type},
                    )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def deleteSolutionImage(self, question, version):
        self.SRmutex.acquire()
        try:
            response = self.delete(
                "/admin/solution",
                json={
                    "user": self.user,
                    "token": self.token,
                    "question": question,
                    "version": version,
                },
            )
            response.raise_for_status()
            if response.status_code == 200:
                return True
            # if response.status_code == 204:
            return False
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    # =====
    # Rubric analysis stuff

    def RgetTestRubricMatrix(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/test_rubric_matrix",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return response.json()

    def RgetRubricCounts(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/rubric/counts",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return response.json()

    def RgetRubricDetails(self, key):
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/REP/rubric/{key}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return response.json()

    # =====
    # Bundle image stuff

    def getBundleFromImage(self, filename):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/bundleFromImage",
                json={"user": self.user, "token": self.token, "filename": filename},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 410:
                raise PlomNoMoreException("Cannot find that image.") from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return response.json()

    def getImagesInBundle(self, bundle_name):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/imagesInBundle",
                json={"user": self.user, "token": self.token, "bundle": bundle_name},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 410:
                raise PlomNoMoreException("Cannot find that bundle.") from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

        return response.json()

    def getPageFromBundle(self, bundle_name, image_position):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/admin/bundlePage",
                json={
                    "user": self.user,
                    "token": self.token,
                    "bundle_name": bundle_name,
                    "bundle_order": image_position,
                },
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
            return image
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 410:
                raise PlomNoMoreException("Cannot find that image / bundle.") from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()
