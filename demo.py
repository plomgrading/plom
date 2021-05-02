# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Victoria Schuster

import os
import shutil
import time
from multiprocessing import Process
import subprocess
from shlex import split
import tempfile
from pathlib import Path

from plom.server import theServer as plomServer


class ServerProcess(Process):
    def run(self):
        plomServer.launch()


class PlomDemo():
    def __init__(self, num_papers=None, scans=True, tmpdir=None):
        """Start up a demo server.

        Args:
            num_papers (int, None): how many papers to use or None for
                a default value.
            scans (bool): whether to fill the demo with fake scanned
                data.
            tmpdir (Path-like, None): a directory for this demo.  If
                omitted a temporary directory of the form
                `plomdemo_<randomstring>`.  Note: by default this
                directory will be removed on demo shutdown.
                TODO: not fully implemented yet!
        """
        if not tmpdir:
            tmpdir = Path(tempfile.mkdtemp(prefix="plomdemo_", dir=os.getcwd()))
        tmpdir = Path(tmpdir)
        # TODO: should either exist and be empty or not exist and we create
        print('making a {}-paper demo in "{}"'.format(num_papers, tmpdir))
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
            subprocess.check_call(split("plom-server init"))
            subprocess.check_call(split("plom-server users --demo"))
            subprocess.check_call(
                split("plom-build new --demo --demo-num-papers {}".format(self._numpapers))
            )
        finally:
            os.chdir(cwd)
        # TODO: maybe ServerProcess should do this itself?
        try:
            os.chdir(self.tmpdir)
            self.srv_proc = ServerProcess()
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
            subprocess.check_call(split("plom-build class --demo -w 1234"))
            subprocess.check_call(split("plom-build make -w 1234"))
            subprocess.check_call(split("plom-fake-scribbles -w 1234"))
            for f in (
                    "fake_scribbled_exams1",
                    "fake_scribbled_exams2",
                    "fake_scribbled_exams3",
            ):
                subprocess.check_call(
                    split("plom-scan process -w 4567 --no-gamma-shift {}.pdf".format(f))
                )
            subprocess.check_call(split("plom-scan upload -w 4567 -u {}".format(f)))
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
    def __init__(self):
        super().__init__(3)




demo = QuickDemo()

print("*"*80)
print("Server is alive?: {}".format(demo.srv_proc.is_alive()))
print("Server PID: {}".format(demo.srv_proc.pid))


# run tests, or whatever
time.sleep(5)


print("*"*80)
print("Stopping server process")
demo.stop()
