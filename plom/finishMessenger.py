# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

import requests

from plom.plom_exceptions import (
    PlomSeriousException,
    PlomAuthenticationException,
)
from plom.managerMessenger import ManagerMessenger

# TODO: how to do this in subclass?
# TODO: set username method?
# _userName = "manager"

# ----------------------


class FinishMessenger(ManagerMessenger):
    """Finishing-related communications.

    TODO: should we merge these few methods into ManagerMessenger?  Issue #2152.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def RgetCompletions(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/completions",
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

    def RgetCoverPageInfo(self, test):
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/REP/coverPageInfo/{test}",
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

    def RgetOriginalFiles(self, testNumber):
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/REP/originalFiles/{testNumber}",
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

    def MgetAllMax(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/MK/allMax",
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

    def getFilesInAllTests(self):
        with self.SRmutex:
            try:
                response = self.get(
                    "/REP/filesInAllTests",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code in (401, 403):
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None
