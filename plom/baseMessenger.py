# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee

from io import BytesIO
import logging
import os
import threading

import requests
from requests_toolbelt import MultipartDecoder
import urllib3

from plom import __version__, Plom_API_Version, Default_Port
from plom import undo_json_packing_of_version_map
from plom.plom_exceptions import PlomBenignException, PlomSeriousException
from plom.plom_exceptions import (
    PlomAPIException,
    PlomAuthenticationException,
    PlomBadTagError,
    PlomConflict,
    PlomConnectionError,
    PlomExistingLoginException,
    PlomNoSolutionException,
    PlomServerNotReady,
    PlomSSLError,
    PlomTaskChangedError,
    PlomTaskDeletedError,
)

log = logging.getLogger("messenger")
# requests_log = logging.getLogger("urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


class BaseMessenger:
    """Basic communication with a Plom Server.

    Handles authentication and other common tasks; subclasses can add
    other features.
    """

    def __init__(self, s=None, port=Default_Port, verify_ssl=True):
        """Initialize a new BaseMessenger.

        Args:

        Keyword Arguments:
            verify_ssl (True/False/str): controls where SSL certs are
                checked, see the `requests` library parameter `verify`
                which ultimately receives this.
        """
        self.session = None
        self.user = None
        self.token = None
        self.default_timeout = (10, 60)
        if s:
            server = s
        else:
            server = "127.0.0.1"
        self.server = "{}:{}".format(server, port)
        self.SRmutex = threading.Lock()
        # base = "https://{}:{}/".format(s, mp)
        self.verify_ssl = verify_ssl
        if not self.verify_ssl:
            self._shutup_urllib3()

    def _shutup_urllib3(self):
        # If we use unverified ssl certificates we get lots of warnings,
        # so put in this to hide them.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @classmethod
    def clone(cls, m):
        """Clone an existing messenger, keeps token.

        In particular, we have our own mutex.
        """
        log.debug("cloning a messeger, but building new session...")
        x = cls(
            s=m.server.split(":")[0],
            port=m.server.split(":")[1],
            verify_ssl=m.verify_ssl,
        )
        x.start()
        log.debug("copying user/token into cloned messenger")
        x.user = m.user
        x.token = m.token
        return x

    def force_ssl_unverified(self):
        """This connection (can be open) does not need to verify cert SSL going forward"""
        self.verify_ssl = False
        if self.session:
            self.session.verify = False
        self._shutup_urllib3()

    def whoami(self):
        return self.user

    def get(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.get(f"https://{self.server}" + url, *args, **kwargs)

    def post(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.post(f"https://{self.server}" + url, *args, **kwargs)

    def put(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.put(f"https://{self.server}" + url, *args, **kwargs)

    def delete(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.delete(f"https://{self.server}" + url, *args, **kwargs)

    def patch(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.patch(f"https://{self.server}" + url, *args, **kwargs)

    def start(self):
        """Start the messenger session.

        Returns:
            str: the version string of the server,
        """
        if self.session:
            log.debug("already have an requests-session")
        else:
            log.debug("starting a new requests-session")
            self.session = requests.Session()
            # TODO: not clear retries help: e.g., requests will not redo PUTs.
            # More likely, just delays inevitable failures.
            self.session.mount("https://", requests.adapters.HTTPAdapter(max_retries=2))
            self.session.verify = self.verify_ssl

        try:
            try:
                response = self.get("/Version", timeout=2)
                response.raise_for_status()
                return response.text
            except requests.exceptions.SSLError as err:
                if os.environ.get("PLOM_NO_SSL_VERIFY"):
                    log.warning("Server SSL cert self-signed/invalid: skip via env var")
                elif "dev" in __version__:
                    log.warning(
                        "Server SSL cert self-signed/invalid: skip b/c dev client"
                    )
                else:
                    raise PlomSSLError(err) from None
                self.force_ssl_unverified()
                response = self.get("/Version", timeout=2)
                response.raise_for_status()
                return response.text
        except requests.ConnectionError as err:
            raise PlomConnectionError(err) from None
        except requests.exceptions.InvalidURL as err:
            raise PlomConnectionError(f"Invalid URL: {err}") from None

    def stop(self):
        """Stop the messenger"""
        if self.session:
            log.debug("stopping requests-session")
            self.session.close()
            self.session = None

    def isStarted(self):
        return bool(self.session)

    def get_server_version(self):
        """The version info of the server.

        Returns:
            str: the version string of the server,

        Exceptions:
        """
        with self.SRmutex:
            try:
                response = self.get("/Version")
                response.raise_for_status()
                return response.text
            except requests.HTTPError as e:
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    # ------------------------
    # ------------------------
    # Authentication stuff

    def requestAndSaveToken(self, user, pw):
        """Get a authorisation token from the server.

        The token is then used to authenticate future transactions with the server.

        raises:
            PlomAPIException: a mismatch between server/client versions.
            PlomExistingLoginException: user already has a token:
                currently, we do not support getting another one.
            PlomAuthenticationException: wrong password, account
                disabled, etc: check contents for details.
            PlomSeriousException: something else unexpected such as a
                network failure.
        """
        self.SRmutex.acquire()
        try:
            response = self.put(
                f"/users/{user}",
                json={
                    "user": user,
                    "pw": pw,
                    "api": Plom_API_Version,
                    "client_ver": __version__,
                },
                timeout=5,
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            self.token = response.json()
            self.user = user
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException(response.json()) from None
            elif response.status_code == 400:
                raise PlomAPIException(response.json()) from None
            elif response.status_code == 409:
                raise PlomExistingLoginException(response.json()) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        except requests.ConnectionError as err:
            raise PlomSeriousException(
                f"Cannot connect to server {self.server}\n{err}\n\nPlease check details and try again."
            ) from None
        finally:
            self.SRmutex.release()

    def clearAuthorisation(self, user, pw):
        self.SRmutex.acquire()
        try:
            response = self.delete(
                "/authorisation", json={"user": user, "password": pw}
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def closeUser(self):
        """User self-indicates they are logging out, surrender token and tasks.

        Raises:
            PlomAuthenticationException: Ironically, the user must be
                logged in to call this.  A second call will raise this.
            PlomSeriousException: other problems such as trying to close
                another user, other than yourself.
        """
        self.SRmutex.acquire()
        try:
            response = self.delete(
                f"/users/{self.user}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    # ----------------------
    # ----------------------
    # Test information

    def getInfoShortName(self):
        """The short name of the exam.

        Returns:
            str: the short name of the exam.

        Exceptions:
            PlomServerNotReady: Server does not have name because it
                does not yet have a spec.
            PlomSeriousException: any other errors.
        """
        with self.SRmutex:
            try:
                response = self.get("/info/shortName")
                response.raise_for_status()
                return response.text
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomServerNotReady(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def get_spec(self):
        """Get the specification of the exam from the server.

        Returns:
            dict: the server's spec file, as in :func:`plom.SpecVerifier`.

        Exceptions:
            PlomServerNotReady: server does not yet have a spec.
        """
        with self.SRmutex:
            try:
                response = self.get("/info/spec")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomServerNotReady(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def getQuestionVersionMap(self, papernum):
        """Get the question-version map for one paper.

        Returns:
            dict: keys are question number (`int`) and values are their
            version (`int`).  Note the raw API call uses strings for
            keys b/c of JSON (transport) limitations but this function
            converts them for us.

        Raises:
            PlomServerNotReady: server does not yet have a version map,
                e.g., b/c it has not been built, or server has no spec.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    f"/admin/questionVersionMap/{papernum}",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                elif response.status_code == 409:
                    raise PlomServerNotReady(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None
        # JSON casts dict keys to str, force back to ints
        return {int(q): v for q, v in response.json().items()}

    def getGlobalQuestionVersionMap(self):
        """Get the question-version map for all papers.

        Returns:
            dict: keys are the paper numbers (`int`) and each value is a row
            of the version map: another dict with questions as question
            number (`int`) and value version (`int`).  Note the raw API call
            uses strings for keys b/c of JSON (transport) limitations but
            this function converts them for us.

        Raises:
            PlomServerNotReady: server does not yet have a version map,
                e.g., b/c it has not been built, or server has no spec.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    "/admin/questionVersionMap",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                elif response.status_code in (404, 409):
                    raise PlomServerNotReady(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None
        # JSON casts dict keys to str, force back to ints
        return undo_json_packing_of_version_map(response.json())

    def IDrequestClasslist(self):
        """Ask server for the classlist.

        Returns:
            list: list of dict, each with at least the keys
                `id` and `studentName` and possibly others.
                Corresponding values are both strings.

        Raises:
            PlomAuthenticationException: login troubles.
            PlomBenignException: server has no classlist.
            PlomSeriousException: all other failures.
        """
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/ID/classlist",
                json={"user": self.user, "token": self.token},
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            # you can assign to the encoding to override the autodetection
            # TODO: define API such that classlist must be utf-8?
            # print(response.encoding)
            # response.encoding = 'utf-8'
            # classlist = StringIO(response.text)
            classlist = response.json()
            return classlist
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 404:
                raise PlomBenignException("Server cannot find the class list") from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def get_all_tags(self):
        """All the tags currently in use and their frequencies.

        Returns:
            dict: keys are tags and values are usage counts.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    "/tags",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def get_tags(self, code):
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/tags/{code}",
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

    def add_single_tag(self, code, tag_text):
        self.SRmutex.acquire()
        try:
            response = self.patch(
                f"/tags/{code}",
                json={"user": self.user, "token": self.token, "tag_text": tag_text},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code in [406, 410]:
                raise PlomBadTagError(response.reason)
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def remove_single_tag(self, code, tag_text):
        self.SRmutex.acquire()
        try:
            response = self.delete(
                f"/tags/{code}",
                json={"user": self.user, "token": self.token, "tag_text": tag_text},
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 410:
                raise PlomBadTagError(response.reason)
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def create_new_tag(self, tag_text):
        self.SRmutex.acquire()
        try:
            response = self.patch(
                "/tags",
                json={"user": self.user, "token": self.token, "tag_text": tag_text},
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code in [406, 409]:
                raise PlomBadTagError(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def McreateRubric(self, new_rubric):
        """Ask server to make a new rubric and get key back.

        Args:
            new_rubric (dict): the new rubric info as dict.

        Raises:
            PlomAuthenticationException: Authentication error.
            PlomSeriousException: Other error types, possible needs fix or debugging.

        Returns:
            list: A list of:
                [False] If operation was unsuccessful.
                [True, updated_commments_list] including the new comments.
        """
        self.SRmutex.acquire()
        try:
            response = self.put(
                "/MK/rubric",
                json={
                    "user": self.user,
                    "token": self.token,
                    "rubric": new_rubric,
                },
            )
            response.raise_for_status()
            new_key = response.json()
            return [True, new_key]
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 406:
                raise PlomSeriousException("Rubric sent was incomplete.") from None
            raise PlomSeriousException(f"Error when creating new rubric: {e}") from None
        finally:
            self.SRmutex.release()

    def MgetRubrics(self):
        """Retrieve list of all rubrics from server.

        Raises:
            PlomAuthenticationException: Authentication error.
            PlomSeriousException: any other unexpected error.

        Returns:
            list: list of dicts, possibly an empty list if server has no
                rubrics.
        """
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/MK/rubric",
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
            raise PlomSeriousException(f"Error getting rubric list: {e}") from None
        finally:
            self.SRmutex.release()

    def MgetRubricsByQuestion(self, question_number):
        """Retrieve list of all rubrics from server for given question.

        Args:
            question_number (int)

        Raises:
            PlomAuthenticationException: Authentication error.
            PlomSeriousException: Other error types, possible needs fix or debugging.

        Returns:
            list: list of dicts, possibly an empty list if server has no
                rubrics for this question.
        """
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/MK/rubric/{question_number}",
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
            raise PlomSeriousException(f"Error getting rubric list: {e}") from None
        finally:
            self.SRmutex.release()

    def MmodifyRubric(self, key, new_rubric):
        """Ask server to modify a rubric and get key back.

        Args:
            rubric (dict): the modified rubric info as dict.

        Raises:
            PlomAuthenticationException: Authentication error.
            PlomSeriousException: Other error types, possible needs fix or debugging.

        Returns:
            list: A list of:
                [False] If operation was unsuccessful.
                [True, updated_commments_list] including the new comments.
        """
        self.SRmutex.acquire()
        try:
            response = self.patch(
                f"/MK/rubric/{key}",
                json={
                    "user": self.user,
                    "token": self.token,
                    "rubric": new_rubric,
                },
            )
            response.raise_for_status()
            new_key = response.json()
            return [True, new_key]

        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 400:
                raise PlomSeriousException("Key mismatch in request.") from None
            elif response.status_code == 406:
                raise PlomSeriousException("Rubric sent was incomplete.") from None
            elif response.status_code == 409:
                raise PlomSeriousException("No rubric with that key found.") from None
            raise PlomSeriousException(
                f"Error of type {e} when creating new rubric"
            ) from None
        finally:
            self.SRmutex.release()

    def request_ID_image(self, code):
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/ID/image/{code}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            if response.status_code == 204:
                return None  # 204 means no image
            return BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.".format(code)
                ) from None
            elif response.status_code == 410:
                raise PlomBenignException(
                    "That ID group of {} has not been scanned.".format(code)
                ) from None
            elif response.status_code == 409:
                raise PlomSeriousException(
                    "Another user has the image for {}. This should not happen".format(
                        code
                    )
                ) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def request_donotmark_images(self, papernum):
        """Get the various Do Not Mark images for a paper."""
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/ID/donotmark_images/{papernum}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            if response.status_code == 204:
                return []  # 204 is empty list
            return [
                BytesIO(img.content).getvalue()
                for img in MultipartDecoder.from_response(response).parts
            ]
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    f"Cannot find DNW image files for {papernum}."
                ) from None
            elif response.status_code == 410:
                raise PlomBenignException(
                    f"The DNM group of {papernum} has not been scanned."
                ) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def get_annotations(self, num, question, edition=None, integrity=None):
        """Download the latest annotations (or a particular set of annotations).

        Args:
            num (int): the paper number.
            question (int): the question number.
            edition (int/None): which annotation set or None for latest.
            integrity (str/None): a checksum to ensure the server hasn't
                changed under us.  Can be omitted if not relevant.

        Returns:
            dict: contents of the plom file.

        Raises:
            PlomAuthenticationException
            PlomTaskChangedError
            PlomTaskDeletedError
            PlomSeriousException
        """
        if edition is None:
            url = f"/annotations/{num}/{question}"
        else:
            url = f"/annotations/{num}/{question}/{edition}"
        if integrity is None:
            integrity = ""
        self.SRmutex.acquire()
        try:
            response = self.get(
                url,
                json={
                    "user": self.user,
                    "token": self.token,
                    "integrity": integrity,
                },
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.".format(num)
                ) from None
            elif response.status_code == 406:
                raise PlomTaskChangedError(
                    "Task {} has been changed by manager.".format(num)
                ) from None
            elif response.status_code == 410:
                raise PlomTaskDeletedError(
                    "Task {} has been deleted by manager.".format(num)
                ) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def get_annotations_image(self, num, question, edition=None):
        """Download image of the latest annotations (or a particular set of annotations).

        Args:
            num (int): the paper number.
            question (int): the question number.
            edition (int/None): which annotation set or None for latest.

        Returns:
            BytesIO: contents of a bitmap file.

        Raises:
            PlomAuthenticationException
            PlomTaskChangedError: TODO: add this back again, with integriy_check??
            PlomTaskDeletedError
            PlomSeriousException
        """
        if edition is None:
            url = f"/annotations_image/{num}/{question}"
        else:
            url = f"/annotations_image/{num}/{question}/{edition}"
        self.SRmutex.acquire()
        try:
            response = self.get(url, json={"user": self.user, "token": self.token})
            response.raise_for_status()
            return BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            elif response.status_code == 404:
                raise PlomSeriousException(
                    "Cannot find image file for {}.".format(num)
                ) from None
            elif response.status_code == 406:
                raise PlomTaskChangedError(
                    "Task {} has been changed by manager.".format(num)
                ) from None
            elif response.status_code == 410:
                raise PlomTaskDeletedError(
                    "Task {} has been deleted by manager.".format(num)
                ) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def getSolutionStatus(self):
        with self.SRmutex:
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

    def getSolutionImage(self, question, version):
        with self.SRmutex:
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
                        f"Server has no solution for question {question} version {version}",
                    ) from None
                return BytesIO(response.content).getvalue()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None
