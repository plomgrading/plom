# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2021 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee

import ssl
import threading
import logging

import urllib3
import requests

from plom import __version__, Plom_API_Version, Default_Port
from plom.plom_exceptions import PlomBenignException, PlomSeriousException
from plom.plom_exceptions import (
    PlomAuthenticationException,
    PlomAPIException,
    PlomExistingLoginException,
)

log = logging.getLogger("messenger")
# requests_log = logging.getLogger("urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

# If we use unverified ssl certificates we get lots of warnings,
# so put in this to hide them.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BaseMessenger:
    """Basic communication with a Plom Server.

    Handles authentication and other common tasks; subclasses can add
    other features.
    """

    def __init__(self, s=None, port=Default_Port):
        sslContext = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        sslContext.check_hostname = False
        # Server defaults
        self.session = None
        self.user = None
        self.token = None
        if s:
            server = s
        else:
            server = "127.0.0.1"
        self.server = "{}:{}".format(server, port)
        self.SRmutex = threading.Lock()
        # base = "https://{}:{}/".format(s, mp)

    @classmethod
    def clone(cls, m):
        """Clone an existing messenger, keeps token."""
        log.debug("cloning a messeger, but building new session...")
        x = cls(s=m.server.split(":")[0], port=m.server.split(":")[1])
        x.start()
        log.debug("copying user/token into cloned messenger")
        x.user = m.user
        x.token = m.token
        return x

    def whoami(self):
        return self.user

    def start(self):
        """Start the messenger session"""
        if self.session:
            log.debug("already have an requests-session")
        else:
            log.debug("starting a new requests-session")
            self.session = requests.Session()
            # TODO - UBC wifi is crappy: have some sort of "hey you've retried
            # nn times already, are you sure you want to keep retrying" message.
            self.session.mount("https://", requests.adapters.HTTPAdapter(max_retries=3))
        try:
            response = self.session.get(
                "https://{}/Version".format(self.server),
                verify=False,
            )
            response.raise_for_status()
        except requests.ConnectionError as err:
            raise PlomBenignException(
                "Cannot connect to server. Please check server details."
            ) from None
        except requests.exceptions.InvalidURL as err:
            raise PlomBenignException(
                "The URL format was invalid. Please try again."
            ) from None
        r = response.text
        return r

    def stop(self):
        """Stop the messenger"""
        if self.session:
            log.debug("stopping requests-session")
            self.session.close()
            self.session = None

    def isStarted(self):
        return bool(self.session)

    # ------------------------
    # ------------------------
    # Authentication stuff

    def requestAndSaveToken(self, user, pw):
        """Get a authorisation token from the server.

        The token is then used to authenticate future transactions with the server.

        """
        self.SRmutex.acquire()
        try:
            response = self.session.put(
                "https://{}/users/{}".format(self.server, user),
                json={
                    "user": user,
                    "pw": pw,
                    "api": Plom_API_Version,
                    "client_ver": __version__,
                },
                verify=False,
                timeout=5,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # convert the content of the response to a textfile for identifier
            self.token = response.json()
            self.user = user
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException(response.json()) from None
            elif response.status_code == 400:  # API error
                raise PlomAPIException(response.json()) from None
            elif response.status_code == 409:
                raise PlomExistingLoginException(response.json()) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        except requests.ConnectionError as err:
            raise PlomSeriousException(
                "Cannot connect to server\n {}\n Please check details before trying again.".format(
                    self.server
                )
            ) from None
        finally:
            self.SRmutex.release()

    def clearAuthorisation(self, user, pw):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/authorisation".format(self.server),
                json={"user": user, "password": pw},
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

    def closeUser(self):
        self.SRmutex.acquire()
        try:
            response = self.session.delete(
                "https://{}/users/{}".format(self.server, self.user),
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

    # ----------------------
    # ----------------------
    # Test information

    def getInfoShortName(self):
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/info/shortName".format(self.server), verify=False
            )
            response.raise_for_status()
            shortName = response.text
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException(
                    "Server could not find the spec - this should not happen!"
                ) from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return shortName

    def get_spec(self):
        """Get the specification of the exam from the server.

        Returns:
            dict: the server's spec file, as in :func:`plom.SpecVerifier`.
        """
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/info/spec".format(self.server),
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException("Server could not find the spec") from None
            else:
                raise PlomSeriousException("Some other sort of error {}".format(e))
        finally:
            self.SRmutex.release()

        return response.json()

    def getInfoGeneral(self):
        """Get some info from pre-0.5.0 server which don't expose the spec.

        Probably we can deprecate or remove this.  Old clients trying to
        talk to newer servers will just get a 404.

        Returns:
            dict: some of the fields of the server's spec file.
        """
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/info/general".format(self.server),
                verify=False,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 404:
                raise PlomSeriousException("Server could not find the spec") from None
            raise PlomSeriousException(
                "Some other sort of error {}".format(e)
            ) from None
        finally:
            self.SRmutex.release()

        pv = response.json()
        fields = (
            "name",
            "numberToProduce",
            "numberOfPages",
            "numberOfQuestions",
            "numberOfVersions",
            "publicCode",
        )
        return dict(zip(fields, pv))

    def IDrequestClasslist(self):
        """Ask server for the classlist.

        Returns:
            list: ordered list of (student id, student name) pairs.
                Both are strings.

        Raises:
            PlomAuthenticationException: login troubles.
            PlomBenignException: server has no classlist.
            PlomSeriousException: all other failures.
        """
        self.SRmutex.acquire()
        try:
            response = self.session.get(
                "https://{}/ID/classlist".format(self.server),
                json={"user": self.user, "token": self.token},
                verify=False,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # you can assign to the encoding to override the autodetection
            # TODO: define API such that classlist must be utf-8?
            # print(response.encoding)
            # response.encoding = 'utf-8'
            # classlist = StringIO(response.text)
            classlist = response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomBenignException("Server cannot find the class list") from None
            else:
                raise PlomSeriousException(
                    "Some other sort of error {}".format(e)
                ) from None
        finally:
            self.SRmutex.release()

        return classlist
