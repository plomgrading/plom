# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

import os
from pathlib import Path
from shlex import split
import subprocess
import tempfile
import time
from warnings import warn

from plom import Default_Port
from plom.server import PlomServer


class PlomDemoServer(PlomServer):
    """Start a Plom demo server.

    For example:

    >>> demo = PlomDemoServer(port=41981, num_papers=5, scans=False)    # doctest: +ELLIPSIS
    Making a 5-paper demo...

    >>> demo.process_is_running()
    True

    >>> demo.pid     # doctest: +SKIP
    14242

    We can then get the credientials needed to interact with the server:
    >>> demo.get_env_vars()    # doctest: +NORMALIZE_WHITESPACE
      {'PLOM_SERVER': 'localhost:41981',
       'PLOM_MANAGER_PASSWORD': '1234',
       'PLOM_SCAN_PASSWORD': '4567',
       'PLOM_USER': 'user0',
       'PLOM_PASSWORD': '0123'}

    We can communicate with the demo server using command line tools:
    >>> import os, subprocess
    >>> env = {**os.environ, **demo.get_env_vars()}
    >>> subprocess.check_call(["plom-scan", "status"], env=env)
    0
    >>> subprocess.call(["plom-finish", "status"], env=env)   # doctest: +SKIP
    1

    (Here these are performed in an interactive Python shell but could
    also be done from the command line).

    TODO: maybe better to give direct (non-subprocess-based) methods.
    TODO: make the demo less random so that we get predictable output from plom-finish.

    Currently its a little more verbose (https://gitlab.com/plom/plom/-/issues/1545)
    but we can also simulate some nonsense student work (TODO: make into doctest)
    ```
    subprocess.check_call(
        split(
            f"python3 -m plom.client.randoMarker "
            f"-s localhost:{demo.port} "
            f"-u {env['PLOM_USER']} -w {env['PLOM_PASSWORD']}"
        ),
        env=env,
    )
    ```

    Finally we stop the server:
    >>> demo.stop()
    Stopping PlomServer ...
    """

    def __init__(self, num_papers=None, port=None, scans=True, tmpdir=None, **kwargs):
        """Start up a Plom demo server.

        Args:
            num_papers (int, None): how many papers to use or None for
                a default value.
            port (int, None): internet port to use or None for default.
            scans (bool): whether to fill the demo with fake scanned
                data.
            tmpdir (Path-like, None): a directory for this demo.  If
                omitted a temporary directory of the form
                `plomdemo_<randomstring>`.  Note: by default this
                directory will be removed on demo shutdown.

        Raises:
            PermissionError: cannot write to `tmpdir`.
            OSError: e.g., address already in use, various others.
            ...
        """
        if not tmpdir:
            tmpdir = Path(tempfile.mkdtemp(prefix="plomdemo_", dir=Path.cwd()))
        tmpdir = Path(tmpdir)
        if any(tmpdir.iterdir()):
            warn("Demo's target directory not empty: likely trouble ahead!")
        self.port = port if port else Default_Port
        # TODO: should either exist and be empty or not exist and we create
        print(f'Making a {num_papers}-paper demo in "{tmpdir}"')
        self._numpapers = num_papers
        # A bunch of class methods to initialize stuff
        self.__class__.initialise_server(tmpdir, port=self.port)
        self.__class__.add_demo_users(tmpdir)
        self.__class__.add_demo_spec(tmpdir, num_to_produce=self._numpapers)
        kwargs.pop("basedir", True)
        super().__init__(basedir=tmpdir, **kwargs)
        if scans:
            self.fill_the_tank()

    def fill_the_tank(self):
        """make fake data and push it into the plom server."""
        env = {**os.environ, **self.get_env_vars()}
        cwd = os.getcwd()
        try:
            os.chdir(self.basedir)
            subprocess.check_call(
                split("python3 -m plom.scripts.build class --demo"), env=env
            )
            subprocess.check_call(split("python3 -m plom.scripts.build make"), env=env)
            # TODO: does not respect env vars (Issue #1545)
            subprocess.check_call(
                split(
                    f"python3 -m plom.produce.faketools -s localhost:{self.port} -w 1234"
                ),
                env=env,
            )
            for f in [f"fake_scribbled_exams{x}" for x in (1, 2, 3)]:
                subprocess.check_call(
                    split(
                        f"python3 -m plom.scripts.scan process --no-gamma-shift {f}.pdf"
                    ),
                    env=env,
                )
            subprocess.check_call(
                split(f"python3 -m plom.scripts.scan upload -u {f}"), env=env
            )
        finally:
            os.chdir(cwd)

    def stop(self, erase_dir=True):
        """Take down the Plom server.

        Args:
            erase_dir (bool): by default, the demo files are deleted.
                Instead you can pass `False` to keep them.
        """
        super().stop(erase_dir=erase_dir)

    def get_env_vars(self):
        """Return the log details for this server as dict."""
        return {
            "PLOM_SERVER": f"localhost:{self.port}",
            "PLOM_MANAGER_PASSWORD": "1234",
            "PLOM_SCAN_PASSWORD": "4567",
            "PLOM_USER": "user0",
            "PLOM_PASSWORD": "0123",
        }


class PlomLiteDemoServer(PlomDemoServer):
    """Quickly start a minimal Plom demo server.

    Tries to start quickly by only using a few papers.  This can be used
    as follows:

    >>> demo = PlomLiteDemoServer(port=41981)     # doctest: +ELLIPSIS
    Making a 3-paper demo...

    >>> demo.process_is_running()
    True

    >>> demo.pid     # doctest: +SKIP
    14242

    Finally we stop the server:
    >>> demo.stop()
    Stopping PlomServer ...

    See also :py:class:`PlomDemoServer`.
    """

    def __init__(self, *args, **kwargs):
        kwargs.pop("num_papers", True)
        super().__init__(*args, num_papers=3, **kwargs)
