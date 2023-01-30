# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021, 2023 Colin B. Macdonald

from pytest import raises

from plom.server import PlomServer


def test_plomserver_must_provide_dir():
    raises(ValueError, lambda: PlomServer())


def test_plomserver_empty_dir(tmpdir):
    raises(FileNotFoundError, lambda: PlomServer(basedir=tmpdir))


# TODO: add more tests about the class methods etc
