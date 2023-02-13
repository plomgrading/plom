# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021, 2023 Colin B. Macdonald

from pytest import raises

from plom.misc_utils import working_directory
from plom.server import build_server_directories, check_server_directories
from plom.server import theServer


def test_make_server_dirs(tmpdir):
    with working_directory(tmpdir):
        build_server_directories()
        check_server_directories()


def test_check_missing_exception(tmpdir):
    with working_directory(tmpdir):
        raises(FileNotFoundError, check_server_directories)


def test_server_launch_wo_dirs(tmpdir):
    with working_directory(tmpdir):
        raises(FileNotFoundError, theServer.launch)
