# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

import os
from multiprocessing import Process
from pathlib import Path
import shutil
import time

from plom import Default_Port
from plom import SpecVerifier
from plom.produce.demotools import buildDemoSourceFiles
from plom.server import theServer
from plom.server import specdir as specdirname

# TODO: move these codes elsewhere?  Out of scripts?
from plom.scripts.server import initialiseServer
from plom.scripts.server import processUsers

"""A background Plom server.

This is a Plom server that forks a background process and returns
control to the caller with the server continuing in the background.
"""


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
