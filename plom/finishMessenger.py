# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

from io import BytesIO

import requests

from plom.plom_exceptions import (
    PlomSeriousException,
    PlomAuthenticationException,
    PlomNoSolutionException,
)
from plom.baseMessenger import BaseMessenger

# TODO: how to do this in subclass?
# TODO: set username method?
# _userName = "manager"

# ----------------------


class FinishMessenger(BaseMessenger):
    """Finishing-related communications."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def RgetCompletionStatus(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/completionStatus",
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

    def RgetOutToDo(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/outToDo",
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

    def RgetSpreadsheet(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/spreadSheet",
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

    def RgetIdentified(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/identified",
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

    def getSolutionStatus(self):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/REP/solutions",
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

    def getSolutionImage(self, question, version):
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/MK/solution",
                json={
                    "user": self.user,
                    "token": self.token,
                    "question": question,
                    "version": version,
                },
            )
            response.raise_for_status()
            if response.status_code == 204:
                raise PlomNoSolutionException(
                    "No solution for {}.{} uploaded".format(question, version)
                ) from None

            img = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()
        return img
