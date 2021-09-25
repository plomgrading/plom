# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald

import requests

from plom.plom_exceptions import PlomSeriousException, PlomAuthenticationException
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
            response = self.session.get(
                "https://{}/REP/completionStatus".format(self.server),
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

    def RgetOutToDo(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/outToDo".format(self.server),
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
                json={
                    "user": self.user,
                    "token": self.token,
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

    def RgetCompletions(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/completions".format(self.server),
                json={
                    "user": self.user,
                    "token": self.token,
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

    def RgetCoverPageInfo(self, test):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/coverPageInfo/{}".format(self.server, test),
                json={
                    "user": self.user,
                    "token": self.token,
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

    def RgetOriginalFiles(self, testNumber):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/REP/originalFiles/{}".format(self.server, testNumber),
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
