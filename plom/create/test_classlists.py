# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald
# Copyright (C) 2022 Andrew Rechnitzer

from pytest import raises
from pathlib import Path

from plom import SpecVerifier

from .classlistValidator import PlomClasslistValidator
from .buildClasslist import clean_non_canvas_csv
from ..misc_utils import working_directory


def test_ok_to_contain_unused_column_names(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name","hungry"\n')
            f.write('12345677,"Doe, Ursula","yes"\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert set(df.columns) == set(("id", "name"))


def test_no_ID_column_fails(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"idZ","studentName"\n')
            f.write('12345678,"Doe"\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        with raises(ValueError):
            _ = clean_non_canvas_csv(foo)


def test_no_name_column_fails(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","studentZZZ"\n')
            f.write('12345678,"Doe"\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        with raises(ValueError):
            _ = clean_non_canvas_csv(foo)


def test_casefold_column_names1(tmpdir):
    # for #1140
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"ID","name"\n')
            f.write('12345677,"Doe, Ursula"\n')
            f.write('12345678,"Doe, Carol"\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert "id" in df.columns
        assert "name" in df.columns
        assert set(df.columns) == set(("id", "name"))


def test_casefold_column_names2(tmpdir):
    # for #1140
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","NaMe"\n')
            f.write('12345678,"Doe"\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert "id" in df.columns
        assert "name" in df.columns
        assert set(df.columns) == set(("id", "name"))


def test_missing_student_info(tmpdir):
    # testing for #1314
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","studentName","hungry"\n')
            f.write('12345677,"Doe, Ursula","yes"\n')
            f.write('87654322,"","who knows"\n')
            f.write('87654323,"A","who knows"\n')
            f.write(',"Doe, John","who knows"\n')
            f.write('"x","Doe, Jan","who knows"\n')

        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert set(df.columns) == set(("id", "name"))
        success, warn_err = vlad.validate_csv(foo, spec=None)
        assert not success
        expected = [
            {
                "warn_or_err": "error",
                "werr_line": 5,
                "werr_text": "SID '' is not an integer, ",
            },
            {
                "warn_or_err": "error",
                "werr_line": 6,
                "werr_text": "SID 'x' is not an integer, ",
            },
            {
                "warn_or_err": "warning",
                "werr_line": 3,
                "werr_text": "Name '' is very short  - please verify.",
            },
            {
                "warn_or_err": "warning",
                "werr_line": 4,
                "werr_text": "Name 'A' is very short  - please verify.",
            },
        ]
        # check these lists against each other - order not important
        assert len(warn_err) == len(expected)
        for X in expected:
            assert X in warn_err


def test_check_classlist_length(tmpdir):
    # Check that classlist is not longer than number to produce
    # should warn that we are not producing enough tests.
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    spec = SpecVerifier.demo(num_to_produce=2)

    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","studentName"\n')
            f.write('12345678,"Doe"\n')
            f.write('12345679,"Doer"\n')
            f.write('12345680,"Doerr"\n')
        success, warn_err = vlad.validate_csv(foo, spec=spec)
        assert success
        expected = [
            {
                "warn_or_err": "warning",
                "werr_line": 0,
                "werr_text": "Classlist is long. Classlist contains 3 names, but spec:numberToProduce is 2",
            }
        ]
        # check these lists against each other - order not important
        assert len(warn_err) == len(expected)
        for X in expected:
            assert X in warn_err


def test_short_name_warning1(tmpdir):
    # for #2052
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"ID","studentName"\n')
            f.write('12345677,"D"\n')
            f.write('12345678,""\n')
        success, warn_err = vlad.validate_csv(foo)
        # should get warnings
        # {'warn_or_err': 'warning', 'werr_line': 2, 'werr_text': "Name 'D' is very short  - please verify."},
        # {'warn_or_err': 'warning', 'werr_line': 3, 'werr_text': "Name '' is very short  - please verify."}

        assert success
        expected = [
            {
                "warn_or_err": "warning",
                "werr_line": 2,
                "werr_text": "Name 'D' is very short  - please verify.",
            },
            {
                "warn_or_err": "warning",
                "werr_line": 3,
                "werr_text": "Name '' is very short  - please verify.",
            },
        ]
        # check these lists against each other - order not important
        assert len(warn_err) == len(expected)
        for X in expected:
            assert X in warn_err


def test_non_latin_name(tmpdir):
    # testing for #1314
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","studentName","hungry"\n')
            f.write('12345677,"Doe, Ursula","yes"\n')
            f.write('12345678,"Doe, 学生","yes"\n')
    success, warn_err = vlad.validate_csv(foo)
    # should get warnings
    # {'warn_or_err': 'warning', 'werr_line': 2, 'werr_text': "Name 'D' is very short  - please verify."},
    # {'warn_or_err': 'warning', 'werr_line': 3, 'werr_text': "Name '' is very short  - please verify."}

    assert success
    expected = [{'warn_or_err': 'warning', 'werr_line': 3, 'werr_text': 'Non-latin characters - Doe, 学生 - Apologies for the eurocentricity.'}]

    # check these lists against each other - order not important
    assert len(warn_err) == len(expected)
    for X in expected:
        assert X in warn_err
