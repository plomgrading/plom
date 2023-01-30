# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2023 Colin B. Macdonald

import os

from plom.server import PlomLiteDemoServer


def setup_module(module):
    # Our CI specifies the env var so why needed?
    os.environ["PLOM_NO_SSL_VERIFY"] = "1"
    # TODO: get a random port from OS instead?
    module.Test.server = PlomLiteDemoServer(
        port=41981, scans=False, backend="multiprocessing"
    )
    module.Test.env = {**os.environ, **module.Test.server.get_env_vars()}


def teardown_module(module):
    module.Test.server.stop(erase_dir=True)


class Test:
    # pylint: disable=no-member
    def test_its_alive(self):
        assert self.server.process_is_running()

    def test_has_pid(self):
        assert self.server.pid

    def test_can_ping(self):
        assert self.server.ping_server()

    def test_can_wait(self):
        assert self.server.wait(0.01) is None
        assert self.server.exitcode is None

    def test_is_multiprocessing(self):
        assert hasattr(self.server, "_server_proc")
        # subprocess has wait, multiprocessing as join
        assert hasattr(self.server._server_proc, "join")
