# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2021 Colin B. Macdonald

"""
Backend bits n bobs to talk to the server
"""

__copyright__ = "Copyright (C) 2018-2021 Andrew Rechnitzer, Colin B. Macdonald et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"


import json
import hashlib
import logging
from io import StringIO, BytesIO

import urllib3
import requests
from requests_toolbelt import MultipartEncoder, MultipartDecoder

from plom.plom_exceptions import PlomSeriousException
from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomConflict,
    PlomTakenException,
    PlomNoMoreException,
    PlomRangeException,
    PlomLatexException,
    PlomTaskChangedError,
    PlomTaskDeletedError,
)

log = logging.getLogger("messenger")
# requests_log = logging.getLogger("urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from plom.baseMessenger import BaseMessenger
from plom.scanMessenger import ScanMessenger
from plom.finishMessenger import FinishMessenger
from plom.managerMessenger import ManagerMessenger


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
        """Return a completed IDing task: identify a paper.

        Exceptions:
            PlomConflict: `studentID` already used on a different paper.
            PlomAuthenticationException: login problems.
            PlomSeriousException: other errors.
        """
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
                raise PlomConflict(e) from None
            elif response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(e) from None
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

    def MclaimThisTask(self, code):
        """Claim a task from server and get back metadata.

        args:
            code (str): a task code such as `"q0123g2"`.

        returns:
            list: Consisting of image_metadata, tags, integrity_check.
        """

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
            ret = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return ret

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

    def MrequestImages(self, code, integrity_check):
        """Download images relevant to a question, both original and annotated.

        Args:
            code (str): the task code such as "q1234g9".

        Returns:
            3-tuple: `(image_metadata, annotated_image, plom_file)`
                `image_metadata` has various stuff: DB ids, md5sums, etc
                `annotated_image` and `plom_file` are the png file and
                and data associated with a previous annotations, or None.

        Raises:
            PlomAuthenticationException
            PlomTaskChangedError: you no longer own this task.
            PlomTaskDeletedError
            PlomSeriousException
        """
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/images/{}".format(self.server, code),
                json={
                    "user": self.user,
                    "token": self.token,
                    "integrity_check": integrity_check,
                },
                verify=False,
            )
            response.raise_for_status()

            # response is either [metadata] or [metadata, annotated_image, plom_file]
            imagesAnnotAndPlom = MultipartDecoder.from_response(response).parts
            image_metadata = json.loads(imagesAnnotAndPlom[0].text)
            if len(imagesAnnotAndPlom) == 1:
                # all is fine - no annotated image or plom data
                anImage = None
                plDat = None
            elif len(imagesAnnotAndPlom) == 3:
                # all fine - last two parts are annotated image + plom-data
                anImage = BytesIO(imagesAnnotAndPlom[1].content).getvalue()
                plDat = BytesIO(imagesAnnotAndPlom[2].content).getvalue()
            else:
                raise PlomSeriousException(
                    "Number of returns doesn't make sense: should be 1 or 3 but is {}".format(
                        len(imagesAnnotAndPlom)
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
                raise PlomTaskChangedError(
                    "Ownership of task {} has changed.".format(code)
                ) from None
            elif response.status_code == 406:
                raise PlomTaskChangedError(
                    "Task {} has been changed by manager.".format(code)
                ) from None
            elif response.status_code == 410:
                raise PlomTaskDeletedError(
                    "Task {} has been deleted by manager.".format(code)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return image_metadata, anImage, plDat

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
                    "Cannot find image file for {}".format(task)
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return imageList

    def MreturnMarkedTask(
        self,
        code,
        pg,
        ver,
        score,
        mtime,
        tags,
        aname,
        pname,
        cname,
        integrity_check,
        image_md5_list,
    ):
        """Upload annotated image and associated data to the server.

        Returns:
            list: a 2-list of the form `[#done, #total]`.

        Raises:
            PlomAuthenticationException
            PlomConflict: integrity check failed, perhaps manager
                altered task.
            PlomTaskChangedError
            PlomTaskDeletedError
            PlomSeriousException
        """
        self.SRmutex.acquire()
        try:
            # doesn't like ints, so convert ints to strings
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
                "integrity_check": integrity_check,
                "image_md5s": image_md5_list,
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
            ret = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 406:
                raise PlomConflict(
                    "Integrity check failed. This can happen if manager has altered the task while you are annotating it."
                ) from None
            elif response.status_code == 409:
                raise PlomTaskChangedError("Task ownership has changed.") from None
            elif response.status_code == 410:
                raise PlomTaskDeletedError(
                    "No such task - it has been deleted from server."
                ) from None
            elif response.status_code == 400:
                raise PlomSeriousException(
                    "Image file is corrupted. This should not happen"
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

    def MrequestWholePaper(self, code, questionNumber=0):
        self.SRmutex.acquire()
        # note - added default value for questionNumber so that this works correctly
        # when called from identifier. - Fixes #921
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
            # TODO?
            elif response.status_code == 409:
                raise PlomTakenException("Task taken by another user.") from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return [pageData, images]

    def MrequestWholePaperMetadata(self, code, questionNumber=0):
        """Get metadata about the images in this paper.

        TODO: questionnumber?  why?

        TODO: returns 404, so why not raise that instead?
        """
        self.SRmutex.acquire()
        # note - added default value for questionNumber so that this works correctly
        # when called from identifier. - Fixes #921
        try:
            response = self.session.get(
                "https://{}/MK/TMP/whole/{}/{}".format(
                    self.server, code, questionNumber
                ),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
            ret = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return ret

    def MrequestOneImage(self, task_code, image_id, md5sum):
        """Download one image from server by its database id.

        args:
            code (str): the task code such as "q1234g9".
                TODO: consider removing code/`task` from URL.
            image_id (int): TODO: int/str?  The key into the server's
                database of images.
            md5sum (str): the expected md5sum, just for sanity checks or
                something I suppose.

        return:
            bytes: png/jpeg or whatever as bytes.

        Errors/Exceptions
            401: not authenticated
            404: no such image
            409: wrong md5sum provided
        """
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/images/{}/{}/{}".format(
                    self.server, task_code, image_id, md5sum
                ),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 409:
                raise PlomConflict("Wrong md5sum provided") from None
            elif response.status_code == 404:
                raise PlomNoMoreException("Cannot find image") from None
            else:
                raise PlomSeriousException(
                    "Some other unexpected error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()
        return image
