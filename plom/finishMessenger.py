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
# _userName = "manager"

# ----------------------


# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FinishMessenger(BaseMessenger):
    """Finishing-related communications."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

    def RgetSpreadsheet(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/spreadSheet".format(self.server),
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

    def RgetIdentified(self):
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

    def RgetCompletions(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/completions".format(self.server),
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

    def RgetCoverPageInfo(self, test):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/coverPageInfo/{}".format(self.server, test),
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

    def RgetAnnotatedFiles(self, testNumber):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/annotatedFiles/{}".format(
                    server, message_port, testNumber
                ),
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

    def RgetOriginalFiles(self, testNumber):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/originalFiles/{}".format(
                    server, message_port, testNumber
                ),
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

    def MgetAllMax(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/MK/allMax".format(self.server),
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
