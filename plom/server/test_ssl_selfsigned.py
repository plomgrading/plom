# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Colin B. Macdonald

from pytest import raises

from plom.server import build_self_signed_SSL_keys


def test_ssl(tmpdir):
    build_self_signed_SSL_keys(tmpdir)


def test_ssl_already_exists(tmpdir):
    build_self_signed_SSL_keys(tmpdir)
    raises(FileExistsError, lambda: build_self_signed_SSL_keys(tmpdir))


def test_ssl_fails_on_garbage(tmpdir):
    raises(
        RuntimeError,
        lambda: build_self_signed_SSL_keys(tmpdir, extra_args="-GARBAGE_INPUT"),
    )
