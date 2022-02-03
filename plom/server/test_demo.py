# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald

import os
from pathlib import Path
from shlex import split
import subprocess

from plom.server import PlomLiteDemoServer


def setup_module(module):
    # TODO: get a random port from OS instead?
    module.Test.demo = PlomLiteDemoServer(port=41981)
    module.Test.env = {**os.environ, **module.Test.demo.get_env_vars()}


def teardown_module(module):
    module.Test.demo.stop()


class Test:
    # pylint: disable=no-member
    def test_its_alive(self):
        assert self.demo.process_is_running()

    def test_has_pid(self):
        assert self.demo.pid

    def test_scan_finish(self):
        # TODO: we should assert something about values or text output here?
        subprocess.check_call(split("python3 -m plom.scan status"), env=self.env)
        r = subprocess.call(split("python3 -m plom.finish status"), env=self.env)
        # TODO: fix up this, seems erratic, perhaps even non-deterministic?
        assert r >= 0  # numScanned - numberComplete
        assert self.demo.process_is_running()

    def test_random_IDing(self):
        subprocess.check_call(split("python3 -m plom.client.randoIDer"), env=self.env)

    def test_get_rubrics_default_extension_is_toml(self, tmpdir):
        f = Path(tmpdir) / "foo"
        subprocess.check_call(
            split(f"python3 -m plom.create rubric --dump {f}"),
            env=self.env,
        )
        assert f.with_suffix(".toml").exists()

    def test_get_rubrics_toml(self, tmpdir):
        f = Path(tmpdir) / "foo.toml"
        subprocess.check_call(
            split(f"python3 -m plom.create rubric --dump {f}"),
            env=self.env,
        )
        assert f.exists()

    def test_put_rubrics_demo(self, tmpdir):
        subprocess.check_call(
            split("python3 -m plom.create rubric --demo"),
            env=self.env,
        )
        f = Path(tmpdir) / "foo.json"
        subprocess.check_call(
            split(f"python3 -m plom.create rubric --dump {f}"),
            env=self.env,
        )
        with open(f, "r") as fh:
            L = fh.readlines()
        assert any("chain rule" in x for x in L)

    def test_random_grading(self):
        subprocess.check_call(split("python3 -m plom.client.randoMarker"), env=self.env)

    def test_scan_finish_after(self):
        subprocess.check_call(split("python3 -m plom.scan status"), env=self.env)
        r = subprocess.call(split("python3 -m plom.finish status"), env=self.env)
        # TODO: fix up this, seems erratic, perhaps even non-deterministic?
        assert r >= 0  # numScanned - numberComplete
        assert self.demo.process_is_running()
