# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021, 2023 Colin B. Macdonald

import ssl

from pytest import raises

from plom.server import build_self_signed_SSL_keys


def test_ssl(tmp_path):
    build_self_signed_SSL_keys(tmp_path)


def test_ssl_already_exists(tmp_path):
    build_self_signed_SSL_keys(tmp_path)
    with raises(FileExistsError):
        build_self_signed_SSL_keys(tmp_path)


def test_ssl_made_files(tmp_path):
    # from pathlib import Path
    # tmp_path = Path("/home/cbm/src/plom/plom.git")
    build_self_signed_SSL_keys(tmp_path)
    key = tmp_path / "plom-selfsigned.key"
    cert = tmp_path / "plom-selfsigned.crt"

    assert key.is_file()
    assert cert.is_file()

    with open(key, "r") as f:
        s = "".join(f.readlines())
    assert "PRIVATE KEY" in s

    with open(cert, "r") as f:
        s = "".join(f.readlines())
    assert "CERTIFICATE" in s


def test_ssl_files_work_in_ssl_context(tmp_path):
    build_self_signed_SSL_keys(tmp_path)
    key = tmp_path / "plom-selfsigned.key"
    cert = tmp_path / "plom-selfsigned.crt"

    ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(cert, key)
    assert isinstance(ssl_context.cert_store_stats(), dict)


def test_ssl_mix_and_match_is_bad(tmp_path):
    dir1 = tmp_path / "foo"
    dir2 = tmp_path / "bar"
    dir1.mkdir()
    dir2.mkdir()

    build_self_signed_SSL_keys(dir1)
    key = dir1 / "plom-selfsigned.key"
    assert key.is_file()

    build_self_signed_SSL_keys(dir2)
    cert = dir2 / "plom-selfsigned.crt"

    ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
    with raises(ssl.SSLError):
        ssl_context.load_cert_chain(cert, key)
