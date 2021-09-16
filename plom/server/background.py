# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster
# Copyright (C) 2020-2021 Forest Kobayashi

"""A background Plom server.

This is a Plom server that forks a background process and returns
control to the caller with the server continuing in the background.
"""

import os
from multiprocessing import Process
from pathlib import Path
from shlex import split
import shutil
import subprocess
import time

import toml

from plom import Default_Port
from plom import SpecVerifier
from plom.misc_utils import working_directory
from plom.produce.demotools import buildDemoSourceFiles
from plom.server import theServer
from plom.server import specdir as specdirname
from plom.server import confdir
from plom.server.prepare import initialise_server
from plom.messenger import Messenger
from plom.plom_exceptions import PlomBenignException


# Ideas from Forest Kobayashi's plom-form-canvas script: ensure the
# server dies with the python script (e.g., if we kill the script.)
# LINUX ONLY I think. See https://stackoverflow.com/a/19448096
# See also https://gitlab.com/plom/plom/-/issues/804
#
# import signal
# import ctypes
#
# libc = ctypes.CDLL("libc.so.6")
#
# def _set_pdeathsig(sig=signal.SIGTERM):
#     """
#     For killing subprocess.Popen() things when python dies
#
#     See https://stackoverflow.com/a/19448096
#     """
#     def callable():
#         return libc.prctl(1, sig)
#     return callable
#
# Popen(..., preexec_fn=_set_pdeathsig(signal.SIGTERM),


class _PlomServerProcess(Process):
    def __init__(self, basedir):
        super().__init__()
        self.basedir = basedir

    def run(self):
        theServer.launch(self.basedir, logfile="server.log", logconsole=False)


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
        initialise_server(basedir, port)

    initialize_server = initialise_server

    @classmethod
    def add_demo_users(cls, basedir):
        """Add users to a Plom server, roughly equivalent to `plom-server users` on cmdline.

        TODO: add features or other class methods to do other user settings.

        Args:
            basedir (Path-like/str): the base directory for the server.
        """
        # TODO: move these codes elsewhere?  Out of scripts?
        from plom.server.__main__ import processUsers

        basedir = Path(basedir)
        basedir.mkdir(exist_ok=True)
        with working_directory(basedir):
            processUsers(None, True, False, False)

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

    def __init__(self, basedir=None, backend=None):
        """Start up Plom server to run in a separate process.

        Args:
            basedir (Path-like/str): the base directory for the server.
                Currently this must exist (use `plom-server init` etc).
                TODO: if does not exist, create and fill?
            backend (str/None): Controls the precise mechanism used to put
                the server into the background.  Probably you should not
                need to use this.  Can be the strings `"subprocess"` or
                `"multiprocessing"`.  Omit or set to None to choose the
                default (currently `"subprocess"`; subject to change).

        TODO: add: quiet (bool): log to file but not console/stderr.  default True?

        Raises:
            PermissionError: cannot write to `dir`.
            OSError: e.g., address already in use, various others.
            ...
        """
        if not basedir:
            raise ValueError('You must provide a directory as the "basedir" parameter')
        self.basedir = Path(basedir)

        if backend is None:
            backend = "subprocess"
        if backend == "subprocess":
            self._pymp = False
        elif backend == "multiprocessing":
            self._pymp = True
        else:
            raise ValueError(f'background backend of "{backend}" is not supported')

        # TODO: if its empty we need to prepare?
        # if not any(self.basedir.iterdir()):
        #     print(f"PlomServer directory {dir} is empty: preparing demo")

        with open(self.basedir / confdir / "serverDetails.toml") as f:
            self.server_info = toml.load(f)

        if self._pymp:
            self._server_proc = _PlomServerProcess(self.basedir)
            self._server_proc.start()
        else:
            self._server_proc = subprocess.Popen(
                split(
                    f"python3 -m plom.server launch {self.basedir} --no-logconsole --logfile server.log"
                )
            )
        assert self.process_is_running(), "The server did not start successfully"
        time.sleep(0.2)
        assert self.process_is_running(), "The server did not start successfully"
        if not self.ping_server():
            # TODO: try to kill it?
            raise RuntimeError("The server did not successfully start")
        assert self.process_is_running(), "The server did not start successfully"

    def process_is_running(self):
        """Forked/background process not yet dead.

        This just checks that the process is still running.  You probably
        want :py:method:`ping_server` to know if the server is responding.
        """
        if self._pymp:
            return self._server_proc.is_alive()
        # for subprocess, its a bit trickier
        try:
            self._server_proc.wait(0.01)
        except subprocess.TimeoutExpired:
            return True
        else:
            return False

    @property
    def pid(self):
        return self._server_proc.pid

    @property
    def exitcode(self):
        if self._pymp:
            return self._server_proc.exitcode
        else:
            return self._server_proc.returncode

    def wait(self, timeout=None):
        """Wait aka join on the subprocess, either forever or with a timeout.

        args:
            timeout (None/int/float): how long to wait.  If None, wait
                forever until the process ends.

        return:
            None: either timed out or stopped.  You can check the return
                code to know which, see :py:method:`exitcode`: it will
                be None if we timed-out, otherwise an integer.
        """
        if self._pymp:
            return self._server_proc.join(timeout)
        try:
            self._server_proc.wait(timeout)
        except subprocess.TimeoutExpired:
            return None
        else:
            return None

    @property
    def logfile(self):
        return self.basedir / "server.log"

    def _brief_wait(self, how_long=0.1):
        """Wait briefly on the subprocess, which should not have stopped.

        Returns:
            bool: True if process is still running, False if it stopped
                while we were waiting.
        """
        self.wait(how_long)
        return self.exitcode is None

    def ping_server(self):
        """Try to connect to the background server.

        Sleep in a loop until we can ping the server.  Then, download
        the spec from the server and compare the `publicCode` to the
        local spec file, which helps confirm we are talking to the
        expected server.

        Args:
            TODO: kwargs number of retries etc?
            TODO: verbose kwarg?

        Returns
            bool: False if we cannot get a minimal response from the server.
        """
        m = Messenger(s=self.server_info["server"], port=self.server_info["port"])
        count = 0
        while True:
            if not self.process_is_running():
                return False
            if not self._brief_wait(0.25):
                print("Server died while we waited for ping")
                return False
            try:
                r = m.start()
            except PlomBenignException:
                pass
            else:
                # successfully talked to server so break loop
                break
            count += 1
            if count >= 10:
                print("we tried 10 times but server is not up yet!")
                return False
        if not self.process_is_running():
            return False
        specfile = SpecVerifier.load_verified(
            fname=self.basedir / specdirname / "verifiedSpec.toml"
        )
        spec = m.get_spec()
        if spec["publicCode"] != specfile["publicCode"]:
            print("Server's publicCode doesn't match: wrong server? wrong address?")
            return False
        m.stop()
        return self.process_is_running()

    def __del__(self):
        print(f'Deleting PlomServer object "{self}"')
        # at least once I saw it created without this attrib
        if hasattr(self, "_server_proc"):
            self.stop()

    def stop(self, erase_dir=False):
        """Take down the Plom server.

        Args:
            erase_dir (bool): by default, the files are left behind.
                Instead you can pass `True` to erase them.
                TODO: maybe only subclasses should allow this?
        """
        if self.process_is_running():
            print(f"Stopping PlomServer '{self}' in dir '{self.basedir}'")
            self._server_proc.terminate()
            # TODO: 10 sec timeout, then kill?
            if self._pymp:
                self._server_proc.join()
            else:
                self._server_proc.wait()
        if erase_dir:
            if self.basedir.exists():
                print(f'Erasing Plom server dir "{self.basedir}"')
                shutil.rmtree(self.basedir)
