# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald

import csv
from pathlib import Path
import toml
from pytest import raises

from plom import Default_Port
from plom.server import create_server_config
from plom.server import create_blank_predictions


def test_server_config(tmpdir):
    create_server_config(tmpdir)
    assert Path(tmpdir / "serverDetails.toml").exists()


def test_server_config_exists(tmpdir):
    create_server_config(tmpdir)
    raises(FileExistsError, lambda: create_server_config(tmpdir))


def test_server_config_load(tmpdir):
    tmp_path = Path(tmpdir)
    create_server_config(tmp_path)
    with open(tmp_path / "serverDetails.toml") as f:
        cfg = toml.load(f)
    assert cfg["server"] == "localhost"
    assert cfg["port"] == Default_Port


def test_server_config_alt_port(tmpdir):
    tmp_path = Path(tmpdir)
    create_server_config(tmp_path, port=41980)
    with open(tmp_path / "serverDetails.toml") as f:
        cfg = toml.load(f)
    assert cfg["port"] == 41980


def test_empty_prediction_list(tmpdir):
    create_blank_predictions(tmpdir)
    pl = Path(tmpdir) / "predictionlist.csv"
    assert pl.exists()
    with open(pl, "r") as f:
        count = len(f.readlines())
    assert count == 1


def test_prediction_list_headers(tmpdir):
    create_blank_predictions(tmpdir)
    pl = Path(tmpdir) / "predictionlist.csv"
    with open(pl, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            assert set(row.keys) == set(["test", "id"])
