# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

import os
from pytest import raises

from plom.server import build_server_directories, check_server_directories
from plom.server import theServer


def test_make_server_dirs(tmpdir):
    cdir = os.getcwd()
    os.chdir(tmpdir)
    build_server_directories()
    check_server_directories()
    os.chdir(cdir)


def test_check_missing_exception(tmpdir):
    cdir = os.getcwd()
    os.chdir(tmpdir)
    raises(FileNotFoundError, check_server_directories)
    os.chdir(cdir)


def test_server_launch_wo_dirs(tmpdir):
    cdir = os.getcwd()
    os.chdir(tmpdir)
    raises(FileNotFoundError, theServer.launch)
    os.chdir(cdir)
