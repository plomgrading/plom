#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
import ssl
import threading
import urllib3
import mimetypes

import toml
import requests
from requests_toolbelt import MultipartEncoder

from plom.plom_exceptions import *
from plom.messenger import BaseMessenger

# TODO: how to do this in subclass?
# TODO: set username method?
# _userName = "scanner"

# ----------------------


# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ScanMessenger(BaseMessenger):
    """Scanner-related communications."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def declareBundle(self, bundle_name, md5sum):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/bundle".format(self.server),
                json={
                    "user": self.user,
                    "token": self.token,
                    "bundle": bundle_name,
                    "md5sum": md5sum,
                },
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

        return response.json()

    def uploadTestPage(self, code, test, page, version, sname, fname, md5sum, bundle):
        self.SRmutex.acquire()
        try:
            param = {
                "user": self.user,
                "token": self.token,
                "fileName": sname,
                "test": test,
                "page": page,
                "version": version,
                "md5sum": md5sum,
                "bundle": bundle,
            }
            mime_type = mimetypes.guess_type(sname)[0]
            dat = MultipartEncoder(
                fields={
                    "param": json.dumps(param),
                    "originalImage": (sname, open(fname, "rb"), mime_type),  # image
                }
            )
            response = self.session.put(
                "https://{}/admin/testPages/{}".format(self.server, code),
                json={"user": self.user, "token": self.token},
                data=dat,
                headers={"Content-Type": dat.content_type},
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

        return response.json()

    def uploadHWPage(self, sid, question, order, sname, fname, md5sum, bundle):
        self.SRmutex.acquire()
        try:
            param = {
                "user": self.user,
                "token": self.token,
                "fileName": sname,
                "sid": sid,
                "question": question,
                "order": order,
                "md5sum": md5sum,
                "bundle": bundle,
            }
            mime_type = mimetypes.guess_type(sname)[0]
            dat = MultipartEncoder(
                fields={
                    "param": json.dumps(param),
                    "originalImage": (sname, open(fname, "rb"), mime_type),  # image
                }
            )
            response = self.session.put(
                "https://{}/admin/hwPages".format(self.server),
                json={"user": self.user, "token": self.token},
                data=dat,
                headers={"Content-Type": dat.content_type},
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

        return response.json()

    def uploadLPage(self, sid, order, sname, fname, md5sum):
        self.SRmutex.acquire()
        try:
            param = {
                "user": self.user,
                "token": self.token,
                "fileName": sname,
                "sid": sid,
                "order": order,
                "md5sum": md5sum,
            }
            mime_type = mimetypes.guess_type(sname)[0]
            dat = MultipartEncoder(
                fields={
                    "param": json.dumps(param),
                    "originalImage": (sname, open(fname, "rb"), mime_type),  # image
                }
            )
            response = self.session.put(
                "https://{}/admin/lPages".format(self.server),
                json={"user": self.user, "token": self.token},
                data=dat,
                headers={"Content-Type": dat.content_type},
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

        return response.json()

    def uploadUnknownPage(self, sname, fname, order, md5sum, bundle):
        self.SRmutex.acquire()
        try:
            param = {
                "user": self.user,
                "token": self.token,
                "fileName": sname,
                "order": order,
                "md5sum": md5sum,
                "bundle": bundle,
            }
            mime_type = mimetypes.guess_type(sname)[0]
            dat = MultipartEncoder(
                fields={
                    "param": json.dumps(param),
                    "originalImage": (sname, open(fname, "rb"), mime_type),  # image
                }
            )
            response = self.session.put(
                "https://{}/admin/unknownPages".format(self.server),
                data=dat,
                headers={"Content-Type": dat.content_type},
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

        return response.json()

    def uploadCollidingPage(self, code, test, page, version, sname, fname, md5sum):
        self.SRmutex.acquire()
        try:
            param = {
                "user": self.user,
                "token": self.token,
                "fileName": sname,
                "test": test,
                "page": page,
                "version": version,
                "md5sum": md5sum,
            }
            mime_type = mimetypes.guess_type(sname)[0]
            dat = MultipartEncoder(
                fields={
                    "param": json.dumps(param),
                    "originalImage": (sname, open(fname, "rb"), mime_type),  # image
                }
            )
            response = self.session.put(
                "https://{}/admin/collidingPages/{}".format(self.server, code),
                data=dat,
                headers={"Content-Type": dat.content_type},
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

    def getUnusedTests(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/unused".format(self.server),
                verify=False,
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            else:
                raise PlomSeriousException("Some other sort of error {}".format(e))
        finally:
            self.SRmutex.release()

        return response.json()

    def getIncompleteTests(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/incomplete".format(self.server),
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

    def getMissingHW(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/missingHW".format(self.server),
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

    def sendTUploadDone(self):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/testPagesUploaded".format(self.server),
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

    def sendHWUploadDone(self):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/hwPagesUploaded".format(self.server),
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

    def sendLUploadDone(self):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/loosePagesUploaded".format(self.server),
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

    def replaceMissingHWQuestion(self, sid, q):
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/admin/missingHWQuestion".format(self.server),
                verify=False,
                json={
                    "user": self.user,
                    "token": self.token,
                    "question": q,
                    "sid": sid,
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
            elif response.status_code == 409:  # that question already has pages
                raise PlomTakenException() from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return rval
