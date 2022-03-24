# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

from pathlib import Path
import tempfile
from warnings import warn

from plom import Default_Port
from plom import SpecVerifier
from plom.misc_utils import working_directory
from plom.server import PlomServer
import plom.scan
import plom.create


class PlomDemoServer(PlomServer):
    """Start a Plom demo server.

    For example:

    >>> demo = PlomDemoServer(port=41981, num_papers=5, scans=False)   # doctest: +ELLIPSIS
    Making a 5-paper demo...

    >>> demo.process_is_running()
    True

    >>> demo.pid     # doctest: +SKIP
    14242

    The randomly-generated directory name of the server:
    >>> str(demo.basedir)    # doctest: +SKIP
    /home/user/plomdemo_s7j9x

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

    We can upload a classlist to our server:
    >>> subprocess.check_call(["plom-create", "class", "--demo"], env=env)
    0

    (Here these are performed in an interactive Python shell but could
    also be done from the command line).

    Build papers
    >>> from plom.create import build_database, build_papers
    >>> build_database(msgr=(env["PLOM_SERVER"], env["PLOM_MANAGER_PASSWORD"]))   # doctest: +ELLIPSIS
    Add DB row for paper 0001: ...

    >>> build_papers(msgr=(env["PLOM_SERVER"], env["PLOM_MANAGER_PASSWORD"]), basedir=demo.basedir)   # doctest: +ELLIPSIS
    Building 2 pre-named papers and 3 blank papers in ...

    We can also simulate some nonsense student work:
    >>> from plom.create import make_scribbles
    >>> make_scribbles(msgr=(env["PLOM_SERVER"], env["PLOM_MANAGER_PASSWORD"]), basedir=demo.basedir)   # doctest: +ELLIPSIS
    Annotating papers with fake student data and scribbling on pages...

    This can also be run from the command line using
    `python3 -m plom.create.exam_scribbler`.

    At that point, we can connect a Plom Client and do some marking.

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
        kwargs.pop("basedir", True)
        super().__init__(basedir=tmpdir, **kwargs)
        s = f'{self.server_info["server"]}:{self.port}'
        pwd = self.get_env_vars()["PLOM_MANAGER_PASSWORD"]
        # TODO: probably want `with Messenger(...) as msgr:` here
        msgr = plom.create.start_messenger(s, pwd, verify_ssl=False)
        try:
            sv = SpecVerifier.demo(num_to_produce=self._numpapers)
            sv.verifySpec()
            sv.checkCodes()
            msgr.upload_spec(sv.spec)
            self.add_demo_sources()
            plom.create.upload_demo_rubrics(msgr=msgr)
        finally:
            msgr.closeUser()
            msgr.stop()
        if scans:
            self.fill_with_fake_scribbled_tests()

    def fill_with_fake_scribbled_tests(self):
        """Simulate the writing of a test by random scribbling and push to the server."""
        s = f'{self.server_info["server"]}:{self.port}'
        scan_pwd = self.get_env_vars()["PLOM_SCAN_PASSWORD"]
        pwd = self.get_env_vars()["PLOM_MANAGER_PASSWORD"]
        # TODO: probably want `with Messenger(...) as msgr:` here
        msgr = plom.create.start_messenger(s, pwd, verify_ssl=False)
        try:
            # grab the spec - needed for classlist parsing
            spec = msgr.get_spec()
            plom.create.upload_demo_classlist(spec, msgr=msgr)
            # cmdline: "plom-create makedb" and "plom-create make"
            status = plom.create.build_database(msgr=msgr)
            print("Database built with output:")
            print(status)
            plom.create.build_papers(basedir=self.basedir, msgr=msgr)
            plom.create.make_scribbles(basedir=self.basedir, msgr=msgr)
        finally:
            msgr.closeUser()
            msgr.stop()
        with working_directory(self.basedir):
            msgr = plom.scan.start_messenger(s, scan_pwd, verify_ssl=False)
            try:
                for f in [f"fake_scribbled_exams{n}.pdf" for n in (1, 2, 3)]:
                    plom.scan.processScans(f, gamma=False, msgr=msgr)
                    plom.scan.uploadImages(f, do_unknowns=True, msgr=msgr)
            finally:
                msgr.closeUser()
                msgr.stop()

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
