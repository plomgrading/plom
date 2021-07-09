# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

import os
from multiprocessing import Process
from pathlib import Path
from shlex import split
import shutil
import subprocess
import tempfile
import time
from warnings import warn

from plom import Default_Port
from plom import SpecVerifier
from plom.produce.demotools import buildDemoSourceFiles
from plom.server import theServer
from plom.server import specdir as specdirname

# TODO: move these codes elsewhere?  Out of scripts?
from plom.scripts.server import initialiseServer
from plom.scripts.server import processUsers


class _PlomServerProcess(Process):
    def run(self):
        theServer.launch()


class PlomServer:
    @classmethod
    def initialise_server(cls, basedir, port=None):
        """Prepare a directory for a Plom server, roughly equivalent to `plom-server init` on cmdline.

        Args:
            port (int, None): internet port to use or None for default.
            basedir (Path-like/str): the base directory for the server.
                TODO: error/warning if it exists!
        """
        basedir = Path(basedir)
        basedir.mkdir(exist_ok=True)
        port = port if port else Default_Port

        cwd = os.getcwd()
        try:
            os.chdir(basedir)
            initialiseServer(port)
        finally:
            os.chdir(cwd)

    initialize_server = initialise_server

    @classmethod
    def add_demo_users(cls, basedir):
        """Add users to a Plom server, roughly equivalent to `plom-server users` on cmdline.

        TODO: add features or other class methods to do other user settings.

        Args:
            basedir (Path-like/str): the base directory for the server.
        """
        basedir = Path(basedir)
        basedir.mkdir(exist_ok=True)
        cwd = os.getcwd()
        try:
            os.chdir(basedir)
            processUsers(None, True, False, False)
        finally:
            os.chdir(cwd)

    @classmethod
    def add_demo_spec(cls, basedir, num_to_produce=10):
        """Add a spec file to a Plom server, roughly equivalent to `plom-build parse` cmdline.

        TODO: add features or other class methods?

        Args:
            basedir (Path-like/str): the base directory for the server.
            num_to_produce (int): the number of papers in the demo,
                defaults to 10.
        """
        basedir = Path(basedir)
        basedir.mkdir(exist_ok=True)
        specdir = basedir / specdirname
        specdir.mkdir(exist_ok=True)
        SpecVerifier.create_demo_template(
            basedir / "demoSpec.toml", num_to_produce=num_to_produce
        )
        sv = SpecVerifier.from_toml_file(basedir / "demoSpec.toml")
        sv.verifySpec()
        sv.checkCodes()
        sv.saveVerifiedSpec(verbose=True, basedir=basedir)
        if not buildDemoSourceFiles(basedir):
            raise RuntimeError("failed to build demo sources")

    def __init__(self, dir=None):
        """Start up Plom server to run in a separate process.

        Args:
            dir (Path-like/str): the base directory for the server.
                Currently this must exist (use `plom-server init` etc).
                TODO: if does not exist, create and fill?

        Raises:
            PermissionError: cannot write to `dir`.
            OSError: e.g., address already in use, various others.
            ...
        """
        if not dir:
            raise ValueError('You must provide a directory as the "dir" parameter')
        self.dir = Path(dir)

        # TODO: if its empty we need to prepare?
        # if not any(self.dir.iterdir()):
        #     print(f"PlomServer directory {dir} is empty: preparing demo")

        # TODO: is there a nice ContextManager to change CWD?
        cwd = os.getcwd()
        # TODO: maybe ServerProcess should do this itself?
        try:
            os.chdir(self.dir)
            self.srv_proc = _PlomServerProcess()
            self.srv_proc.start()
        finally:
            os.chdir(cwd)
            # TODO: sleep in a loop until we can "ping"?
        time.sleep(2)
        assert self.srv_proc.is_alive()

    def stop(self, erase_dir=False):
        """Take down the Plom server.

        Args:
            erase_dir (bool): by default, the files are left behind.
                Instead you can pass `True` to erase them.
                TODO: maybe only subclasses should allow this?
        """
        self.srv_proc.terminate()
        self.srv_proc.join()
        if erase_dir:
            print(f'Erasing Plom server dir "{dir}"')
            shutil.rmtree(self.dir)


class PlomDemo(PlomServer):
    def __init__(self, num_papers=None, port=None, scans=True, tmpdir=None):
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
            tmpdir = Path(tempfile.mkdtemp(prefix="plomdemo_", dir=os.getcwd()))
        tmpdir = Path(tmpdir)
        if any(tmpdir.iterdir()):
            warn("Demo's target directory not empty: likely touble ahead!")
        self.port = port if port else Default_Port
        # TODO: should either exist and be empty or not exist and we create
        print(f'Making a {num_papers}-paper demo in "{tmpdir}"')
        self._numpapers = num_papers
        # A bunch of class methods to initialize stuff
        self.__class__.initialise_server(tmpdir, port=self.port)
        self.__class__.add_demo_users(tmpdir)
        self.__class__.add_demo_spec(tmpdir, num_to_produce=self._numpapers)
        super().__init__(dir=tmpdir)
        if scans:
            self.fill_the_tank()

    def fill_the_tank(self):
        """make fake data and push it into the plom server."""
        env = {**os.environ, **self.get_env_vars()}
        cwd = os.getcwd()
        try:
            os.chdir(self.dir)
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


class PlomQuickDemo(PlomDemo):
    """Quickly start a Plom demo server.

    Tries to start quickly by only using a few papers.
    """

    def __init__(self, port=None):
        super().__init__(3, port=port)


if __name__ == "__main__":
    demo = PlomQuickDemo(port=41981)

    print("*" * 80)
    print("Server is alive?: {}".format(demo.srv_proc.is_alive()))
    print("Server PID: {}".format(demo.srv_proc.pid))

    env = {**os.environ, **demo.get_env_vars()}
    subprocess.check_call(split("plom-scan status"), env=env)
    subprocess.check_call(split("plom-finish status"), env=env)

    print("*" * 80)
    print("Starting some random IDing and random grading...")
    subprocess.check_call(
        split(
            f"python3 -m plom.client.randoIDer "
            f"-s localhost:{demo.port} "
            f"-u {env['PLOM_USER']} -w {env['PLOM_PASSWORD']}"
        ),
        env=env,
    )
    subprocess.check_call(
        split(
            f"python3 -m plom.client.randoMarker "
            f"-s localhost:{demo.port} "
            f"-u {env['PLOM_USER']} -w {env['PLOM_PASSWORD']}"
        ),
        env=env,
    )
    subprocess.check_call(split("plom-scan status"), env=env)
    subprocess.check_call(split("plom-finish status"), env=env)

    time.sleep(5)

    print("*" * 80)
    print("Stopping server process")
    demo.stop()
