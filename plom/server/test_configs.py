# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2023 Colin B. Macdonald
# Copyright (C) 2022 Andrew Rechnitzer

from pathlib import Path
from pytest import raises
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from plom import Default_Port
from plom.server import create_server_config


def test_server_config(tmpdir):
    create_server_config(tmpdir)
    assert Path(tmpdir / "serverDetails.toml").exists()


def test_server_config_exists(tmpdir):
    create_server_config(tmpdir)
    raises(FileExistsError, lambda: create_server_config(tmpdir))


def test_server_config_load(tmpdir):
    tmp_path = Path(tmpdir)
    create_server_config(tmp_path)
    with open(tmp_path / "serverDetails.toml", "rb") as f:
        cfg = tomllib.load(f)
    assert cfg["server"] == "localhost"
    assert cfg["port"] == Default_Port


def test_server_config_alt_port(tmpdir):
    tmp_path = Path(tmpdir)
    create_server_config(tmp_path, port=41980)
    with open(tmp_path / "serverDetails.toml", "rb") as f:
        cfg = tomllib.load(f)
    assert cfg["port"] == 41980
