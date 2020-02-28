#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import os
import requests
from requests_toolbelt import MultipartEncoder
import ssl
import threading
import toml
import urllib3

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

    def uploadKnownPage(self, code, test, page, version, sname, fname, md5sum):
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
            dat = MultipartEncoder(
                fields={
                    "param": json.dumps(param),
                    "originalImage": (sname, open(fname, "rb"), "image/png"),  # image
                }
            )
            response = self.session.put(
                "https://{}/admin/knownPages/{}".format(self.server, code),
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

    def uploadUnknownPage(self, sname, fname, md5sum):
        self.SRmutex.acquire()
        try:
            param = {
                "user": self.user,
                "token": self.token,
                "fileName": sname,
                "md5sum": md5sum,
            }
            dat = MultipartEncoder(
                fields={
                    "param": json.dumps(param),
                    "originalImage": (sname, open(fname, "rb"), "image/png"),  # image
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
            dat = MultipartEncoder(
                fields={
                    "param": json.dumps(param),
                    "originalImage": (sname, open(fname, "rb"), "image/png"),  # image
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
