# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2021 Peter Lee
# Copyright (C) 2022 Michael Deakin
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Tam Nguyen
# Copyright (C) 2024 Bryan Tanady

from __future__ import annotations

from io import BytesIO
import logging
import os
import threading
from typing import Any

import requests
import urllib3

from plom import __version__
from plom import Plom_API_Version
from plom import Plom_Legacy_Server_API_Version
from plom import Default_Port
from plom import undo_json_packing_of_version_map
from plom.plom_exceptions import PlomSeriousException
from plom.plom_exceptions import (
    PlomAPIException,
    PlomAuthenticationException,
    PlomBadTagError,
    PlomConflict,
    PlomConnectionError,
    PlomExistingLoginException,
    PlomInconsistentRubric,
    PlomNoClasslist,
    PlomNoMoreException,
    PlomNoPaper,
    PlomNoPermission,
    PlomNoRubric,
    PlomNoSolutionException,
    PlomRangeException,
    PlomServerNotReady,
    PlomSSLError,
    PlomTaskChangedError,
    PlomTaskDeletedError,
    PlomNoServerSupportException,
)

log = logging.getLogger("messenger")
# requests_log = logging.getLogger("urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


class BaseMessenger:
    """Basic communication with a Plom Server.

    Handles authentication and other common tasks; subclasses can add
    other features.

    Instance Variables:
        token (str/dict/Any): on legacy, this was just a string.  On
            the django-based server, its a dict with a single key
            ``"token"`` and value a string.
    """

    def __init__(
        self,
        server: str | None = None,
        *,
        port: int | None = None,
        scheme: str | None = None,
        verify_ssl: bool = True,
        webplom: bool | None = None,
    ) -> None:
        """Initialize a new BaseMessenger.

        Args:
            server: URL or None to default to localhost.

        Keyword Arguments:
            port: What port to try to connect to.  Defaults
                to 41984 if omitted and cannot be determined from the
                URI string.
            scheme: What scheme to use to connect.  Defaults
                to ``"https"`` if omitted and cannot be determined from
                the URI string.
            verify_ssl (True/False): controls where SSL certs are
                checked, see the `requests` library parameter
                ``Session.verify`` which ultimately receives this.
            webplom: whether to connect to a newer
                Django-based server.  If ``False``, force connection to a
                legacy server.  If ``True``, force connect to a new server.
                The default (recommended!) is ``None``, to autodetect.

        Returns:
            None

        Raises:
            PlomConnectionError
        """
        self.webplom = webplom

        if not server:
            server = "127.0.0.1"

        # Issue 3051: e.g. trailing control characters or whitespace
        server = server.strip()

        try:
            parsed_url = urllib3.util.parse_url(server)
        except urllib3.exceptions.LocationParseError as e:
            raise PlomConnectionError(f'Cannot parse the URL "{server}"') from e

        if not parsed_url.host:
            # "localhost:1234" parses this way: we do it ourselves :(
            if scheme is None:
                scheme = "https"
            self._raw_init(f"{scheme}://{server}", verify_ssl=verify_ssl)
            return

        # prefix with "https://" if not specified
        if not parsed_url.scheme:
            if scheme is None:
                scheme = "https"
            server = f"{scheme}://{server}"

        # postfix with default port if not specified
        if not parsed_url.port:
            if port is None:
                port = Default_Port
            server = f"{server}:{port}"

        self._raw_init(server, verify_ssl=verify_ssl)

    def _raw_init(self, base: str, *, verify_ssl: bool) -> None:
        self.session: requests.Session | None = None
        self.user: str | None = None
        # on legacy, it is a string, modern server it is a dict
        self.token: str | dict[str, str] | None = None
        self.default_timeout = (10, 60)
        try:
            parsed_url = urllib3.util.parse_url(base)
        except urllib3.exceptions.LocationParseError as e:
            raise PlomConnectionError(f'Cannot parse the URL "{base}"') from e
        self.scheme = parsed_url.scheme
        self.base = base
        self.SRmutex = threading.Lock()
        self.verify_ssl = verify_ssl
        if not self.verify_ssl:
            self._shutup_urllib3()

    def _shutup_urllib3(self) -> None:
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
            m.base,
            verify_ssl=m.verify_ssl,
            webplom=m.webplom,
        )
        x.start()
        log.debug("copying user/token into cloned messenger")
        x.user = m.user
        x.token = m.token
        return x

    def is_ssl_verified(self) -> bool:
        return self.verify_ssl

    def force_ssl_unverified(self) -> None:
        """This connection (can be open) does not need to verify cert SSL going forward."""
        self.verify_ssl = False
        if self.session:
            self.session.verify = False
        self._shutup_urllib3()

    def whoami(self) -> str | None:
        return self.user

    @property
    def username(self) -> str | None:
        return self.whoami()

    def enable_legacy_server_support(self) -> None:
        if self.token:
            raise RuntimeError('cannot change "legacy" status after login')
        self.webplom = False

    def disable_legacy_server_support(self) -> None:
        if self.token:
            raise RuntimeError('cannot change "legacy" status after login')
        self.webplom = True

    def is_legacy_server(self) -> bool | None:
        if self.webplom is None:
            return None
        return not self.webplom

    @property
    def server(self) -> str:
        return self.base

    def get(self, url: str, *args, **kwargs) -> requests.Response:
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout

        # Legacy servers expect "user" and "token" in the json.
        # Now with django we pass a token in the header.
        # TODO: rework this when/if we stop supporting legacy servers.
        if self.webplom and "json" in kwargs and "token" in kwargs["json"]:
            if not self.token:
                raise PlomAuthenticationException("Trying auth'd operation w/o token")
            assert isinstance(self.token, dict)
            token_str = self.token["token"]
            kwargs["headers"] = {"Authorization": f"Token {token_str}"}
            json = kwargs["json"]
            json.pop("token")
            kwargs["json"] = json

        assert self.session
        return self.session.get(self.base + url, *args, **kwargs)

    def get_auth(self, url: str, *args, **kwargs) -> requests.Response:
        """Perform a GET method on a URL with a token for authentication."""
        if self.is_legacy_server():
            raise RuntimeError("This routine does not work on legacy servers")
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        if not self.token:
            raise PlomAuthenticationException("Trying auth'd operation w/o token")
        assert isinstance(self.token, dict)
        kwargs["headers"] = {"Authorization": f"Token {self.token['token']}"}
        assert self.session
        return self.session.get(self.base + url, *args, **kwargs)

    def post_raw(self, url: str, *args, **kwargs) -> requests.Response:
        """Perform a POST method without tokens."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout

        assert self.session
        return self.session.post(self.base + url, *args, **kwargs)

    def post_auth(self, url: str, *args, **kwargs) -> requests.Response:
        """Perform a POST method on a URL with a token for authentication."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout

        if not self.token:
            raise PlomAuthenticationException("Trying auth'd operation w/o token")

        if self.webplom:
            assert isinstance(self.token, dict)
            # Django-based servers pass token in the header
            token_str = self.token["token"]
            kwargs["headers"] = {"Authorization": f"Token {token_str}"}
        else:
            # Legacy servers expect "user" and "token" in the json.
            json = kwargs.get("json", {})
            json["user"] = self.user
            json["token"] = self.token
            kwargs["json"] = json

        assert self.session
        return self.session.post(self.base + url, *args, **kwargs)

    def put(self, url: str, *args, **kwargs) -> requests.Response:
        """Perform a PUT method on a URL."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout

        if self.webplom and "json" in kwargs and "token" in kwargs["json"]:
            if not self.token:
                raise PlomAuthenticationException("Trying auth'd operation w/o token")
            assert isinstance(self.token, dict)
            token_str = self.token["token"]
            kwargs["headers"] = {"Authorization": f"Token {token_str}"}
            json = kwargs["json"]
            json.pop("token")
            kwargs["json"] = json

        assert self.session
        return self.session.put(self.base + url, *args, **kwargs)

    def delete(self, url: str, *args, **kwargs) -> requests.Response:
        """Perform a DELETE method on a URL."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout

        if self.webplom and "json" in kwargs and "token" in kwargs["json"]:
            if not self.token:
                raise PlomAuthenticationException("Trying auth'd operation w/o token")
            assert isinstance(self.token, dict)
            token_str = self.token["token"]
            kwargs["headers"] = {"Authorization": f"Token {token_str}"}
            json = kwargs["json"]
            json.pop("token")
            kwargs["json"] = json

        assert self.session
        return self.session.delete(self.base + url, *args, **kwargs)

    def patch(self, url: str, *args, **kwargs) -> requests.Response:
        """Perform a PATCH method on a URL."""
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout

        if self.webplom and "json" in kwargs and "token" in kwargs["json"]:
            if not self.token:
                raise PlomAuthenticationException("Trying auth'd operation w/o token")
            assert isinstance(self.token, dict)
            token_str = self.token["token"]
            kwargs["headers"] = {"Authorization": f"Token {token_str}"}
            json = kwargs["json"]
            json.pop("token")
            kwargs["json"] = json

        assert self.session
        return self.session.patch(self.base + url, *args, **kwargs)

    def patch_auth(self, url: str, *args, **kwargs) -> requests.Response:
        """Perform a PATCH method on a URL with a token for authentication."""
        if self.is_legacy_server():
            raise RuntimeError("This routine does not work on legacy servers")
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        if not self.token:
            raise PlomAuthenticationException("Trying auth'd operation w/o token")
        assert isinstance(self.token, dict)
        kwargs["headers"] = {"Authorization": f"Token {self.token['token']}"}
        assert self.session
        return self.session.patch(self.base + url, *args, **kwargs)

    def _start(self) -> str:
        """Start the messenger session, low-level.

        Returns:
            the version string of the server.
        """
        if self.session:
            log.debug("already have an requests-session")
        else:
            log.debug("starting a new requests-session")
            self.session = requests.Session()
            assert self.session
            # TODO: not clear retries help: e.g., requests will not redo PUTs.
            # More likely, just delays inevitable failures.
            self.session.mount(
                f"{self.scheme}://", requests.adapters.HTTPAdapter(max_retries=2)
            )
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

    def start(self) -> str:
        """Start the messenger session, including detecting legacy servers.

        Returns:
            The version string of the server.

        Raises:
            PlomAPIException: server is too old (or maybe just non-existent).
        """
        s = self._start()
        if self.webplom is not None:
            return s
        info = self.get_server_info()
        if "Legacy" in info["product_string"]:
            self.enable_legacy_server_support()
            log.warning("Using legacy messenger to talk to legacy server")
        else:
            self.disable_legacy_server_support()
        return s

    def stop(self) -> None:
        """Stop the messenger."""
        if self.session:
            log.debug("stopping requests-session")
            self.session.close()
            self.session = None

    def isStarted(self) -> bool:
        return bool(self.session)

    def get_server_version(self) -> str:
        """The version info of the server.

        Returns:
            The version string of the server,

        Exceptions:
        """
        with self.SRmutex:
            try:
                response = self.get("/Version")
                response.raise_for_status()
                return response.text
            except requests.HTTPError as e:
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def get_server_info(self) -> dict[str, Any]:
        """Get a dictionary of server software information.

        Returns:
            Key-value pairs of information about the server software.

        Exceptions:
            PlomAPIException: 404, maybe there is no server, or its too
                old to support the server info API call.
        """
        with self.SRmutex:
            try:
                response = self.get("/info/server")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 404:
                    raise PlomAPIException(
                        f"Server info not found: server too old?\n{e}"
                    ) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    # ------------------------
    # ------------------------
    # Authentication stuff
    def get_user_role(self) -> str | None:
        """Obtain user's role from the server.

        Args:
            user: the username of the user.

        Raises:
            PlomAuthenticationException
            PlomSeriousException: something unexpected happened.

        Returns:
            If it is legacy server, returns "". Otherwise returns
            either of ["lead_marker", "marker", "scanner", "manager"]
            if the user is recognized.
        """
        if self.is_legacy_server():
            raise PlomNoServerSupportException("Operation not supported in Legacy.")

        path = f"/info/user/{self.user}"
        with self.SRmutex:
            try:
                response = self.get_auth(path)
                # throw errors when response code != 200.
                response.raise_for_status()
                return response.text
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def requestAndSaveToken(self, user: str, pw: str) -> None:
        """Get a authorisation token from the server.

        The token is then used to authenticate future transactions with the server.

        Raises:
            PlomAPIException: a mismatch between server/client versions.
            PlomExistingLoginException: user already has a token:
                currently, we do not support getting another one on
                legacy servers.  TBD on the new server.
            PlomAuthenticationException: wrong password, account
                disabled, etc: check contents for details.
            PlomSeriousException: something else unexpected such as a
                network failure.
        """
        if self.webplom:
            self._requestAndSaveToken_webplom(user, pw)
        else:
            self._requestAndSaveToken_legacy(user, pw)

    def _requestAndSaveToken_legacy(self, user: str, pw: str) -> None:
        self.SRmutex.acquire()
        try:
            response = self.put(
                f"/users/{user}",
                json={
                    "user": user,
                    "pw": pw,
                    "api": Plom_Legacy_Server_API_Version,
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
                f"Cannot connect to server {self.base}\n{err}\n\nPlease check details and try again."
            ) from None
        finally:
            self.SRmutex.release()

    def _requestAndSaveToken_webplom(self, user: str, pw: str) -> None:
        """Get an authorisation token from WebPlom."""
        with self.SRmutex:
            response = self.post_raw(
                "/get_token/",
                json={
                    "username": user,
                    "password": pw,
                    "api": Plom_API_Version,
                    "client_ver": __version__,
                },
                timeout=5,
            )
            try:
                response.raise_for_status()
                self.token = response.json()
                self.user = user
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                elif response.status_code == 400:
                    raise PlomAPIException(response.reason) from None
                elif response.status_code == 409:
                    # TODO: not sure django-server prevents simultaneous logins
                    raise PlomExistingLoginException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None
            except requests.ConnectionError as err:
                raise PlomSeriousException(
                    f"Cannot connect to server {self.base}\n{err}\n\n"
                    "Please check details and try again."
                ) from None

    def clearAuthorisation(self, user: str, pw: str) -> None:
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

    def closeUser(self) -> None:
        """User self-indicates they are logging out, surrender token and tasks.

        Raises:
            PlomAuthenticationException: Ironically, the user must be
                logged in to call this.  A second call will raise this.
            PlomSeriousException: other problems such as trying to close
                another user, other than yourself.
        """
        if self.webplom:
            path = "/close_user/"
        else:
            path = f"/users/{self.user}"
        with self.SRmutex:
            try:
                response = self.delete(
                    path,
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None
            self.token = None

    # ----------------------
    # ----------------------
    # Test information

    def get_exam_info(self) -> dict[str, Any]:
        """Get a dictionary of information about this assessment.

        Returns:
            Key-value pairs of information about this particular
            assessment.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    "/info/exam",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def get_spec(self) -> dict:
        """Get the specification of the exam from the server.

        Returns:
            The server's spec, as in :func:`plom.SpecVerifier`.

        Exceptions:
            PlomServerNotReady: server does not yet have a spec.
        """
        with self.SRmutex:
            try:
                if self.is_legacy_server():
                    response = self.get("/info/spec")
                else:
                    response = self.get_auth("/info/spec")
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomServerNotReady(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def getMaxMark(self, question):
        """Get the maximum mark for this question.

        Raises:
            PlomRangeException: `question` is out of range or non-integer.
            PlomAuthenticationException:
            PlomSeriousException: something unexpected happened.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    f"/maxmark/{question}",
                    json={"user": self.user, "token": self.token},
                )
                # throw errors when response code != 200.
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 400:
                    raise PlomRangeException(response.reason) from None
                if response.status_code == 416:
                    raise PlomRangeException(response.reason) from None
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
                    f"/plom/admin/questionVersionMap/{papernum}",
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
            If we don't yet have a version map, the result is an empty dict.

        Raises:
            PlomAuthenticationException: login troubles.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    "/plom/admin/questionVersionMap",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None
        # JSON casts dict keys to str, force back to ints
        return undo_json_packing_of_version_map(response.json())

    def IDrequestClasslist(self):
        """Ask server for the classlist.

        Returns:
            list: list of dict, each with at least the keys
            `id`, `name`, `paper_number`, and possibly others.
            Corresponding values are str, str, and integer.

        Raises:
            PlomAuthenticationException: login troubles.
            PlomNoClasslist: server has no classlist.
            PlomSeriousException: any other unexpected failures.
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
                raise PlomAuthenticationException(response.reason) from None
            if response.status_code == 404:
                raise PlomNoClasslist(response.reason) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()

    def IDgetPredictions(self):
        """Get all the predicted student ids.

        If there is more than one predictor for a particular paper number
        this routine will return all of them.
        You may want :meth:`IDgetPredictionsFromPredictor` instead.

        Returns:
            dict: keys are str of papernum, values themselves are lists of dicts with
            keys `"student_id"`, `"certainty"`, and `"predictor"`.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    "/ID/predictions",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                # returns a json of dict of test:(sid, sname, certainty)
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def IDgetPredictionsFromPredictor(self, predictor):
        """Get all the predicted student ids, generated by a particular predictor.

        Args:
            predictor (string): predictors are currently `"prename"` and
                `"MLLAP"`.  These are subject to change.  If there are no
                predictions or you pass some other string, you'll get an
                empty dict.

        Returns:
            dict: keys are str of papernum, values themselves dicts with
            keys `"student_id"`, `"certainty"`, and `"predictor"`.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    f"/ID/predictions/{predictor}",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def sid_to_paper_number(self, student_id) -> tuple[bool, int | str, str]:
        """Ask server to match given student_id to a test-number.

        This is callable only by "manager" and "scanner" users and currently
        only implemented on legacy servers.

        The test number could be b/c the paper is IDed.  Or it could be a
        prediction (a confident one, currently "prename").  The third
        argument can be used to distinguish which case (if the server is
        new enough: needs > 0.14.1).

        Note: we check ID'd first so if the paper is ID'd you'll
        get that (even if ``student_id`` is also used in a prename.
        If its not ID'd but its prenamed, there can be more than one
        prename pointing to the same paper.  In this case, you'll
        get one of them; its not well-defined which.

        Returns:
            If we found a paper then ``(True, test_number, how)`` where
            ``how`` is a string "ided" or "prenamed" (or on older servers
            <= 0.14.1 we'll get an apology that we don't know.).
            If no paper then, we get
            ``(False, 'Cannot find test with that student id', '')``.

        Raises:
            PlomAuthenticationException: wrong user, wrong token etc.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    "/plom/admin/sidToTest",
                    json={
                        "user": self.user,
                        "token": self.token,
                        "sid": student_id,
                    },
                )
                response.raise_for_status()
                r = response.json()
                # TODO: could remove workaround when we stop supported 0.14.1
                if len(r) <= 2:
                    if r[0]:
                        r.append("[Older server; cannot tell if ided or prenamed]")
                    else:
                        r.append("")
                r = tuple(r)
                return r
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

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
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def get_tags(self, code):
        """Get a list of tags associated with a paper and question.

        Args:
            code (str): For example "q0009g3" for paper number 9, question 3.
                TODO: consider passing paper_num and question instead of this
                nonsense.

        Returns:
            list: a list of strings, one for each tag.  If there are no tags,
            you get an empty list.
            On some legacy servers, if the task was not found, you get ``None``
            rather than an exception.

        Raises:
            PlomNoPaper: the task was not found (or was poorly formed
                in the request).
        """
        with self.SRmutex:
            try:
                response = self.get(
                    f"/tags/{code}",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code in (404, 406):
                    raise PlomNoPaper(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def add_single_tag(self, code: str, tag_text: str) -> None:
        """Add a tag to a task.

        Args:
            code: e.g., like ``q0013g1``, for paper 13 question 1.
            tag_text: the tag.

        Returns:
            None

        Raises:
            PlomAuthenticationException
            PlomBadTagError: invalid tag (such as disallowed chars).
                Also no such task, or invalid formed task code.
        """
        with self.SRmutex:
            try:
                response = self.patch(
                    f"/tags/{code}",
                    json={"user": self.user, "token": self.token, "tag_text": tag_text},
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code in (406, 404, 410):
                    raise PlomBadTagError(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def remove_single_tag(self, task, tag_text):
        """Remove a tag from a task.

        Args:
            task (str): e.g., like ``q0013g1``, for paper 13 question 1.
            tag_text (str): the tag.

        Returns:
            None

        Raises:
            PlomAuthenticationException
            PlomConflict: no such task
        """
        with self.SRmutex:
            try:
                response = self.delete(
                    f"/tags/{task}",
                    json={
                        "user": self.user,
                        "token": self.token,
                        "tag_text": tag_text,
                    },
                )
                response.raise_for_status()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                if response.status_code == 404:
                    raise PlomNoPaper(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

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

    def McreateRubric(self, new_rubric: dict[str, Any]) -> dict[str, Any]:
        """Ask server to make a new rubric and get key back.

        Args:
            new_rubric: the new rubric info as dict.  The server will
                probably add other fields so you should not consider
                this input data as canonical.  Instead, call back and
                get the new rubric.

        Raises:
            PlomAuthenticationException: Authentication error.
            PlomSeriousException: Other error types, possible needs fix or debugging.

        Returns:
            The dict key-value representation of the new rubric.  This is
            generally not the same as the input data, for example, it has an
            key/id.
        """
        with self.SRmutex:
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
                new_rubric = response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                elif response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                if response.status_code == 406:
                    raise PlomSeriousException(response.reason) from None
                raise PlomSeriousException(
                    f"Error when creating new rubric: {e}"
                ) from None
        if self.is_legacy_server():
            # On legacy servers, `new_rubric` will actually just be the key
            assert isinstance(new_rubric, str)
            return self.get_one_rubric(new_rubric)
        return new_rubric

    def MgetOtherRubricUsages(self, key: str) -> list[int]:
        """Retrieve list of paper numbers using the given rubric.

        Note: This only returns papers whose most recent annotation
        use the rubric.

        Args:
            key: The identifier of the rubric.

        Returns:
            the list of paper numbers using the rubric, or an empty
            list if no papers are using the rubric.
        """
        if self.is_legacy_server():
            raise PlomNoServerSupportException("Operation not supported in Legacy.")
        with self.SRmutex:
            url = f"/MK/rubric_usage/{key}"
            try:
                response = self.get_auth(url)
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(
                    f"Error getting paper number list: {e}"
                ) from None

    def get_one_rubric(self, key: str) -> dict[str, Any]:
        """Retrieve one rubric from its key.

        I don't think we actually have an endpoint for this.  For now
        we fake it by getting all rubrics and filtering.

        Args:
            key: The key/id of the rubric we want.

        Raises:
            PlomNoRubric: no such rubric.
            PlomAuthenticationException: Authentication error.
            PlomSeriousException: Other error types, possible needs fix or debugging.

        Returns:
            Dict representation of the rubric.
        """
        rubrics = self.MgetRubrics(None)
        try:
            # ensure there is exactly one matching rubric in each list and grab it
            (r,) = [r for r in rubrics if r["id"] == key]
        except ValueError:
            raise PlomNoRubric(f"No rubric with key={key}") from None
        return r

    def MgetRubrics(self, question: int | None = None) -> list[dict[str, Any]]:
        """Retrieve list of all rubrics from server for given question.

        Args:
            question: ``None`` or omit to get all questions.

        Raises:
            PlomAuthenticationException: Authentication error.
            PlomSeriousException: Other error types, possible needs fix or debugging.

        Returns:
            List of dicts, possibly an empty list if server has no
            rubrics for this question.
        """
        if self.is_legacy_server():
            return self._legacy_getRubrics(question)

        with self.SRmutex:
            if question is None:
                url = "/MK/rubrics"
            else:
                url = f"/MK/rubrics/{question}"
            try:
                response = self.get_auth(url)
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 404:
                    raise PlomNoRubric(response.reason) from None
                raise PlomSeriousException(f"Error getting rubric list: {e}") from None

    def _legacy_getRubrics(self, question: int | None = None) -> list[dict[str, Any]]:
        with self.SRmutex:
            if question is None:
                url = "/MK/rubric"
            else:
                url = f"/MK/rubric/{question}"

            try:
                response = self.get(
                    url,
                    json={
                        "user": self.user,
                        "token": self.token,
                    },
                )
                response.raise_for_status()
                rubrics = response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Error getting rubric list: {e}") from None
            # monkey-patch new "system_rubric" field into legacy results
            for r in rubrics:
                if r["username"] in ("HAL", "manager"):
                    r["system_rubric"] = True
                else:
                    r["system_rubric"] = False
                # A special sentinel value for legacy server
                # TODO: annoying b/c downstream needs to detect and not send to arrow
                r.setdefault("last_modified", "unknown")
                r.setdefault("modified_by_username", "")
            return rubrics

    def MmodifyRubric(self, key: str, new_rubric: dict[str, Any]) -> dict[str, Any]:
        """Ask server to modify a rubric and get key back.

        Args:
            key: the key/id of the rubric to change.
            new_rubric: the changes we want to make as a key-value dict.

        Returns:
            The dict key-value representation of the new rubric.  This is
            generally not the same as the input data, for example, it has an
            key/id.  You should use this returned rubric and discard the input.

        Raises:
            PlomAuthenticationException: Authentication error.
            PlomInconsistentRubric:
            PlomNoRubric:
            PlomNoPermission: you are not allowed to modify the rubric.
            PlomConflict: two users try to modify the rubric.
            PlomSeriousException: Other error types, possible needs fix or debugging.
        """
        with self.SRmutex:
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
                new_rubric = response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                elif response.status_code == 400:
                    raise PlomSeriousException(response.reason) from None
                elif response.status_code == 403:
                    raise PlomNoPermission(response.reason) from None
                elif response.status_code == 404:
                    raise PlomNoRubric(response.reason) from None
                elif response.status_code == 406:
                    raise PlomInconsistentRubric(response.reason) from None
                elif response.status_code == 409:
                    if self.is_legacy_server():
                        # legacy sends 409 for not-found
                        raise PlomNoRubric(response.reason) from None
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(
                    f"Error when modifying rubric: {e}"
                ) from None
        if self.is_legacy_server():
            # On legacy servers, `new_rubric` will actually just be the key
            assert isinstance(new_rubric, str)
            return self.get_one_rubric(new_rubric)
        return new_rubric

    def get_pagedata(self, code):
        """Get metadata about the images in this paper."""
        with self.SRmutex:
            try:
                response = self.get(
                    f"/pagedata/{code}",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def get_pagedata_context_question(self, code, questionNumber):
        """Get metadata about all non-ID page images in this paper, as related to a question.

        For now, questionNumber effects the "included" column...

        If the paper wasn't scanned, the result will be an empty list.
        """
        with self.SRmutex:
            try:
                response = self.get(
                    f"/pagedata/{code}/context/{questionNumber}",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                if response.status_code == 409:
                    raise PlomConflict(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def get_image(self, image_id: int, md5sum: str) -> bytes:
        """Download one image from server by its database id.

        Args:
            image_id: TODO: int/str?  The key into the server's
                database of images.
            md5sum: the expected md5sum, just for correctness checks of
                some sort.

        Returns:
            bytes: png/jpeg or whatever as bytes.

        Errors/Exceptions:
            401: not authenticated
            404: no such image
            409: wrong md5sum provided
        """
        self.SRmutex.acquire()
        try:
            response = self.get(
                f"/MK/images/{image_id}/{md5sum}",
                json={"user": self.user, "token": self.token},
            )
            response.raise_for_status()
            image = BytesIO(response.content).getvalue()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 409:
                raise PlomConflict("Wrong md5sum provided") from None
            if response.status_code == 404:
                raise PlomNoMoreException("Cannot find image") from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()
        return image

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
            PlomNoPaper
            PlomSeriousException
        """
        if edition is None:
            url = f"/annotations/{num}/{question}"
        else:
            url = f"/annotations/{num}/{question}/{edition}"
        if integrity is None:
            integrity = ""
        with self.SRmutex:
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
                if response.status_code == 400:
                    raise PlomRangeException(response.reason) from None
                elif response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                elif response.status_code == 404:
                    raise PlomNoPaper(response.reason) from None
                elif response.status_code == 406:
                    raise PlomTaskChangedError(response.reason) from None
                elif response.status_code == 410:
                    raise PlomTaskDeletedError(response.reason) from None
                elif response.status_code == 416:
                    raise PlomRangeException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def get_annotations_image(
        self, num: int, question: int, *, edition: int | None = None
    ) -> tuple[dict, bytes]:
        """Download image of the latest annotations (or a particular set of annotations).

        Args:
            num: the paper number.
            question: the question number.

        Keyword Args:
            edition: which annotation set or None for latest.

        Returns:
            2-tuple, the first being a dictionary with info about the download and
            the second being the raw bytes of a bitmap file.  The dictionary contains
            at least the keys ``extension``and ``Content-Type`` and possibly others.
            For now, ``extension`` will be either ``"png"`` or ``"jpg"``.

        Raises:
            PlomAuthenticationException
            PlomTaskChangedError: TODO: add this back again, with integrity_check??
            PlomTaskDeletedError
            PlomNoPaper
            PlomSeriousException
        """
        if edition is None:
            url = f"/annotations_image/{num}/{question}"
        else:
            url = f"/annotations_image/{num}/{question}/{edition}"
        with self.SRmutex:
            try:
                response = self.get(url, json={"user": self.user, "token": self.token})
                response.raise_for_status()
                info: dict[str, Any] = {}
                info["Content-Type"] = response.headers.get("Content-Type", None)
                if info["Content-Type"] == "image/png":
                    info["extension"] = "png"
                elif info["Content-Type"] == "image/jpeg":
                    info["extension"] = "jpg"
                else:
                    raise PlomSeriousException(
                        "Failed to identify extension of image data for previous annotations"
                    )
                return info, BytesIO(response.content).getvalue()
            except requests.HTTPError as e:
                if response.status_code == 400:
                    raise PlomRangeException(response.reason) from None
                elif response.status_code == 401:
                    raise PlomAuthenticationException(response.reason) from None
                elif response.status_code == 404:
                    raise PlomNoPaper(response.reason) from None
                elif response.status_code == 406:
                    raise PlomTaskChangedError(response.reason) from None
                elif response.status_code == 410:
                    raise PlomTaskDeletedError(response.reason) from None
                elif response.status_code == 416:
                    raise PlomRangeException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

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

    def getSolutionImage(self, question: int, version: int) -> bytes:
        """Download the solution image for a question version.

        Args:
            question: the question number.
            version: the version number.

        Returns:
            contents of a bitmap file.

        Raises:
            PlomAuthenticationException
            PlomNoSolutionException
        """
        with self.SRmutex:
            try:
                if self.is_legacy_server():
                    response = self.get(
                        "/MK/solution",
                        json={
                            "user": self.user,
                            "token": self.token,
                            "question": question,
                            "version": version,
                        },
                    )
                else:
                    response = self.get_auth(f"/MK/solution/{question}/{version}")

                response.raise_for_status()
                # deprecated: new servers will 404
                if response.status_code == 204:
                    raise PlomNoSolutionException(
                        f"Server has no solution for question {question} version {version}",
                    ) from None
                return BytesIO(response.content).getvalue()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                if response.status_code == 404:
                    raise PlomNoSolutionException(response.reason)
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def getUnknownPages(self):
        with self.SRmutex:
            try:
                response = self.get(
                    "/plom/admin/unknownPages",
                    json={
                        "user": self.user,
                        "token": self.token,
                    },
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code in (401, 403):
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def getDiscardedPages(self):
        with self.SRmutex:
            try:
                response = self.get(
                    "/plom/admin/discardedPages",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code in (401, 403):
                    raise PlomAuthenticationException(response.reason) from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None

    def getCollidingPageNames(self):
        with self.SRmutex:
            try:
                response = self.get(
                    "/plom/admin/collidingPageNames",
                    json={"user": self.user, "token": self.token},
                )
                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                if response.status_code == 401:
                    raise PlomAuthenticationException() from None
                raise PlomSeriousException(f"Some other sort of error {e}") from None
