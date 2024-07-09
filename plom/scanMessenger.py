# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald

import json
import mimetypes

import requests
from requests_toolbelt import MultipartEncoder

from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomSeriousException,
    PlomTakenException,
)
from plom.baseMessenger import BaseMessenger

# TODO: how to do this in subclass?
# TODO: set username method?
# _userName = "scanner"

# ----------------------


class ScanMessenger(BaseMessenger):
    """Scanner-related communications."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def doesBundleExist(self, bundle_name, md5sum):
        """Ask server if given bundle exists.

        Checks bundle's md5sum and name:
        * neither = no matching bundle, return [False, None]
        * name but not md5 = return [True, 'name'] - user is trying to upload different bundles with same name.
        * md5 but not name = return [True, 'md5sum'] - user is trying to same bundle with different names.
        * both match = return [True, 'both'] - user could be retrying
          after network failure (for example) or uploading unknown or
          colliding pages.
        """
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/plom/admin/bundle",
                json={
                    "user": self.user,
                    "token": self.token,
                    "bundle": bundle_name,
                    "md5sum": md5sum,
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

    def createNewBundle(self, bundle_name, md5sum):
        """Ask server to create bundle with given name/md5sum.

        Server will check name / md5sum of bundle.
        * If bundle matches either 'name' or 'md5sum' then return [False, reason] - this shouldn't happen if scanner working correctly.
        * If bundle matches 'both' then return [True, skip_list] where skip_list = the page-orders from that bundle that are already in the system. The scan scripts will then skip those uploads.
        * If no such bundle return [True, []] - create the bundle and return an empty skip-list.
        """
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/plom/admin/bundle",
                json={
                    "user": self.user,
                    "token": self.token,
                    "bundle": bundle_name,
                    "md5sum": md5sum,
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

    def listBundles(self):
        """Ask server for list of bundles in database.

        Returns:
            list: a list of dict, each contains the `name`, `md5sum` and
            `numberOfPages` for each bundle.
        """
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/plom/admin/bundle/list",
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

    def uploadTestPage(
        self, code, test, page, version, f, md5sum: str, bundle: str, bundle_order: int
    ):
        """Update a test page which has known page, known paper number, usually QR-coded.

        Typically the page is QR coded, and thus we know precisely what
        paper number, what question and what page.  We may not know the
        student depending on whether it was pre-ided or not.

        Args:
            code (str): a string such as "t0020p06v1".
            test (int): paper number.
            page (int): page number.
            version (int): which version.  Server knows this so probably used
                for sanity checks.
            f (pathlib.Path): file to upload.  Filename is uploaded too.
            md5sum: hash of file's content.
            bundle: the name of a group of images scanned together
                such as a single PDF file.
            bundle_order: this image's place within the bundle (e.g.,
                PDF page number).

        Returns:
            tuple: `(bool, reason, message)`, the bool indicates success.
            Sometimes `message` is actually a list, in the collision case.
        """
        with self.SRmutex:
            try:
                param = {
                    "user": self.user,
                    "token": self.token,
                    "fileName": f.name,
                    "test": test,
                    "page": page,
                    "version": version,
                    "md5sum": md5sum,
                    "bundle": bundle,
                    "bundle_order": bundle_order,
                }
                mime_type = mimetypes.guess_type(f.name)[0]
                with open(f, "rb") as fh:
                    dat = MultipartEncoder(
                        fields={
                            "param": json.dumps(param),
                            "originalImage": (f.name, fh, mime_type),
                        }
                    )
                    response = self.put(
                        f"/plom/admin/testPages/{code}",
                        json={"user": self.user, "token": self.token},
                        data=dat,
                        headers={"Content-Type": dat.content_type},
                    )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        return response.json()

    def uploadHWPage(
        self, sid, questions, order, f, md5sum: str, bundle: str, bundle_order: int
    ):
        """Upload a homework page: self-scanned, known student, and known(-ish) questions.

        This is intended for "homework pages", often self-scanned or
        otherwise less organized than QR-coded pages.  (The page need
        not be strictly speaking homework.)  If you know precisely which
        page this is (e.g., from a QR code), you probably want to upload
        a TestPage instead,

        Typically the page is without QR codes.  The uploader knows what
        student it belongs to and what question(s).  The order within the
        question is somewhat known too, at least within its upload bundle.

        Args:
            sid (str): which student to attach this image to.
            questions (list): a list of questions (ints) to attach to.
            order (int): something like "page number" except that HWPages
                do not map directly onto page numbers.  It is used to order these page
                images in the marker UI for example: pages with smaller order
                are displayed first.  It need not start at 1.  It need not
                increase by ones.  Most likely you can just pass the
                `bundle_order` parameter below here too.
            f (pathlib.Path): the file to be uploaded.
            md5sum: hash of file's content.
            bundle: the name of a group of images scanned together
                such as a single PDF file.
            bundle_order: this image's place within the bundle (e.g.,
                PDF page number).

        Returns:
            list/tuple: a bool indicating success/failure and an error
               message.
        """
        with self.SRmutex:
            try:
                param = {
                    "user": self.user,
                    "token": self.token,
                    "fileName": f.name,
                    "sid": sid,
                    "questions": questions,
                    "order": order,
                    "md5sum": md5sum,
                    "bundle": bundle,
                    "bundle_order": bundle_order,
                }
                mime_type = mimetypes.guess_type(f.name)[0]
                with open(f, "rb") as fh:
                    dat = MultipartEncoder(
                        fields={
                            "param": json.dumps(param),
                            "originalImage": (f.name, fh, mime_type),
                        }
                    )
                    response = self.put(
                        "/plom/admin/hwPages",
                        json={"user": self.user, "token": self.token},
                        data=dat,
                        headers={"Content-Type": dat.content_type},
                    )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        return response.json()

    def uploadUnknownPage(self, f, order, md5sum, bundle, bundle_order):
        with self.SRmutex:
            try:
                param = {
                    "user": self.user,
                    "token": self.token,
                    "fileName": f.name,
                    "order": order,
                    "md5sum": md5sum,
                    "bundle": bundle,
                    "bundle_order": bundle_order,
                }
                mime_type = mimetypes.guess_type(f.name)[0]
                with open(f, "rb") as fh:
                    dat = MultipartEncoder(
                        fields={
                            "param": json.dumps(param),
                            "originalImage": (f.name, fh, mime_type),
                        }
                    )
                    response = self.put(
                        "/plom/admin/unknownPages",
                        data=dat,
                        headers={"Content-Type": dat.content_type},
                    )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        return response.json()

    def uploadCollidingPage(
        self, code, test, page, version, f, md5sum, bundle, bundle_order
    ):
        with self.SRmutex:
            try:
                param = {
                    "user": self.user,
                    "token": self.token,
                    "fileName": f.name,
                    "test": test,
                    "page": page,
                    "version": version,
                    "md5sum": md5sum,
                    "bundle": bundle,
                    "bundle_order": bundle_order,
                }
                mime_type = mimetypes.guess_type(f.name)[0]
                with open(f, "rb") as fh:
                    dat = MultipartEncoder(
                        fields={
                            "param": json.dumps(param),
                            "originalImage": (f.name, fh, mime_type),
                        }
                    )
                    response = self.put(
                        f"/plom/admin/collidingPages/{code}",
                        data=dat,
                        headers={"Content-Type": dat.content_type},
                    )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

        return response.json()

    def getScannedTests(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/scanned",
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

    def getUnusedTests(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/unused",
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

    def getIncompleteTests(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/incomplete",
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

    def getCompleteHW(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/completeHW",
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

    def getMissingHW(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/missingHW",
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

    def replaceMissingHWQuestion(self, student_id=None, test=None, question=None):
        # can replace by SID or by test-number
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/plom/admin/missingHWQuestion",
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
            if response.status_code == 409:  # that question already has pages
                raise PlomTakenException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()
