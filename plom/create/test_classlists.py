# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald

from pytest import raises
from pathlib import Path

from .buildClasslist import clean_non_canvas_csv, check_is_non_canvas_csv
from ..misc_utils import working_directory


def test_multi_column_names(tmpdir):
    tmpdir = Path(tmpdir)
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","Surname","preferredName"\n')
            f.write('12345677,"Doe","Ursula"\n')
            f.write('12345678,"Doe","Carol"\n')
        assert check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert "id" in df.columns
        assert "studentName" in df.columns
        assert set(df.columns) == set(("id", "studentName"))


def test_ok_to_contain_unused_column_names(tmpdir):
    tmpdir = Path(tmpdir)
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","Surname","preferredName","hungry"\n')
            f.write('12345677,"Doe","Ursula","yes"\n')
        assert check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert set(df.columns) == set(("id", "studentName"))


def test_only_one_name_column(tmpdir):
    tmpdir = Path(tmpdir)
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name"\n')
            f.write('12345678,"Doe"\n')
        assert not check_is_non_canvas_csv(foo)
        with raises(ValueError):
            _ = clean_non_canvas_csv(foo)


def test_no_ID_column_fails(tmpdir):
    tmpdir = Path(tmpdir)
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"idZ","studentName"\n')
            f.write('12345678,"Doe"\n')
        assert not check_is_non_canvas_csv(foo)
        with raises(ValueError):
            _ = clean_non_canvas_csv(foo)
