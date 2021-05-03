# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

import os
from shlex import split
import subprocess

from plom.demo import PlomQuickDemo


def setup_module(module):
    # TODO: get a random port from OS instead?
    module.Test.demo = PlomQuickDemo(port=41981)
    module.Test.env = {**os.environ, **module.Test.demo.get_env_vars()}


def teardown_module(module):
    module.Test.demo.stop()


class Test:
    def test_its_alive(self):
        assert self.demo.srv_proc.is_alive()

    def test_has_pid(self):
        assert self.demo.srv_proc.pid

    def test_scan_finish(self):
        # TODO: we should assert something about values or text output here?
        subprocess.check_call(split("plom-scan status"), env=self.env)
        subprocess.check_call(split("plom-finish status"), env=self.env)
        assert self.demo.srv_proc.is_alive()

    def test_random_IDing(self):
        subprocess.check_call(
            split(
                f"python3 -m plom.client.randoIDer "
                f"-s localhost:{self.demo.port} "
                f"-u {self.env['PLOM_USER']} -w {self.env['PLOM_PASSWORD']}"
            ),
            env=self.env,
        )

    def test_random_grading(self):
        subprocess.check_call(
            split(
                f"python3 -m plom.client.randoMarker "
                f"-s localhost:{self.demo.port} "
                f"-u {self.env['PLOM_USER']} -w {self.env['PLOM_PASSWORD']}"
            ),
            env=self.env,
        )

    def test_scan_finish_after(self):
        subprocess.check_call(split("plom-scan status"), env=self.env)
        subprocess.check_call(split("plom-finish status"), env=self.env)
        assert self.demo.srv_proc.is_alive()
