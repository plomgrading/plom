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
from plom.server import theServer as plomServer


class _PlomServerProcess(Process):
    def run(self):
        plomServer.launch()


class PlomDemo:
    def __init__(self, num_papers=None, port=None, scans=True, tmpdir=None):
        """Start up a demo server.

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
                TODO: not fully implemented yet!

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
        print('Making a {}-paper demo in "{}"'.format(num_papers, tmpdir))
        self._numpapers = num_papers
        self.tmpdir = tmpdir
        self._start()
        if scans:
            self.fill_the_tank()

    def _start(self):
        """start the server."""
        # TODO: is there a nice ContextManager to change CWD?
        cwd = os.getcwd()
        try:
            os.chdir(self.tmpdir)
            subprocess.check_call(split(f"plom-server init --port {self.port}"))
            subprocess.check_call(split("plom-server users --demo"))
            subprocess.check_call(
                split(f"plom-build new --demo --demo-num-papers {self._numpapers}")
            )
        finally:
            os.chdir(cwd)
        # TODO: maybe ServerProcess should do this itself?
        try:
            os.chdir(self.tmpdir)
            self.srv_proc = _PlomServerProcess()
            self.srv_proc.start()
        finally:
            os.chdir(cwd)
            # TODO: sleep in a loop until we can "ping"?
        time.sleep(2)
        assert self.srv_proc.is_alive()

    def fill_the_tank(self):
        """make fake data and push it into the plom server."""
        cwd = os.getcwd()
        try:
            env = {
                **os.environ,
                "PLOM_SERVER": f"localhost:{self.port}",
                "PLOM_MANAGER_PASSWORD": "1234",
                "PLOM_SCAN_PASSWORD": "4567",
            }
            subprocess.check_call(split("plom-build class --demo"), env=env)
            subprocess.check_call(split("plom-build make"), env=env)
            # TODO: does not respect env vars (Issue #1545)
            subprocess.check_call(
                split(f"plom-fake-scribbles -s localhost:{self.port} -w 1234"), env=env
            )
            for f in [f"fake_scribbled_exams{x}" for x in (1, 2, 3)]:
                subprocess.check_call(
                    split(f"plom-scan process --no-gamma-shift {f}.pdf"), env=env
                )
            subprocess.check_call(split(f"plom-scan upload -u {f}"), env=env)
        finally:
            os.chdir(cwd)

    def stop(self):
        """Takedown the demo server.

        TODO: add option to leave files behind
        """
        self.srv_proc.terminate()
        self.srv_proc.join()
        self.srv_proc.close()
        # TODO: need to do sth like .wait() or close() did already?
        time.sleep(0.1)
        print('Erasing demo tmpdir "{}"'.format(self.tmpdir))
        shutil.rmtree(self.tmpdir)


class QuickDemo(PlomDemo):
    def __init__(self, port=None):
        super().__init__(3, port=port)


if __name__ == "__main__":
    demo = QuickDemo(port=41981)

    print("*" * 80)
    print("Server is alive?: {}".format(demo.srv_proc.is_alive()))
    print("Server PID: {}".format(demo.srv_proc.pid))

    # run tests, or whatever
    time.sleep(5)

    print("*" * 80)
    print("Stopping server process")
    demo.stop()
