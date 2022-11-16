import threading
import urllib3
import logging
import requests
import os

from plom import __version__
from plom.plom_exceptions import (
    PlomSSLError,
    PlomConnectionError,
    PlomSeriousException,
    PlomAPIException,
    PlomExistingLoginException,
    PlomAuthenticationException,
    PlomServerNotReady,
    PlomRangeException,
)

log = logging.getLogger("messenger")


class WebPlomMessenger:
    """
    Handles communication between the plom QT client and the Django server.
    """

    def __init__(self, s=None, port=8000, *, verify_ssl=True):
        """Initialize a new BaseMessenger.

        Args:
            s (str/None): URL or None to default to localhost.
            port (int): What port to try to connect to.  Defaults
                to 41984 if omitted.

        Keyword Arguments:
            verify_ssl (True/False/str): controls where SSL certs are
                checked, see the `requests` library parameter `verify`
                which ultimately receives this.
        """
        self.scheme = "http"
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

    @property
    def username(self):
        return self.whoami()

    def get(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.get(f"{self.scheme}://{self.server}" + url, *args, **kwargs)

    def post(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.post(
            f"{self.scheme}://{self.server}" + url, *args, **kwargs
        )

    def put(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.put(f"{self.scheme}://{self.server}" + url, *args, **kwargs)

    def delete(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.delete(
            f"{self.scheme}://{self.server}" + url, *args, **kwargs
        )

    def patch(self, url, *args, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.default_timeout
        return self.session.patch(
            f"{self.scheme}://{self.server}" + url, *args, **kwargs
        )

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

    def requestAndSaveToken(self, user, pw):
        """
        Get an authorisation token from WebPlom.
        """
        self.SRmutex.acquire()
        response = self.post(
            "/get_token/",
            json={
                "username": user,
                "password": pw,
            },
            timeout=5,
        )
        try:
            response.raise_for_status()
            self.token = response.json()
            self.user = user
        except requests.HTTPError as e:
            if response.status_code == 400:
                raise PlomAuthenticationException(response.json()) from None
            elif response.status_code == 401:
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

    def MgetMaxMark(self, question, ver):
        """Get the maximum mark for this question and version.

        Raises:
            PlomRangeExeception: `question` or `ver` is out of range or
                non-integer.
            PlomAuthenticationException:
            PlomSeriousException: something unexpected happened.
        """
        self.SRmutex.acquire()
        try:
            response = self.get(
                "/MK/maxMark",
                json={"user": self.user, "token": self.token, "q": question, "v": ver},
            )
            # throw errors when response code != 200.
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise PlomAuthenticationException() from None
            if response.status_code == 400:
                raise PlomRangeException(response.text) from None
            if response.status_code == 416:
                raise PlomRangeException(response.text) from None
            raise PlomSeriousException(f"Some other sort of error {e}") from None
        finally:
            self.SRmutex.release()
