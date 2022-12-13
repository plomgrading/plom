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
            f.write('"id","name","paper_number", "hungry"\n')
            f.write('12345677,"Doe, Ursula","","yes"\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert set(df.columns) == set(("id", "name", "paper_number"))
        success, warn_err = vlad.validate_csv(foo, spec=None)
        assert success
        assert warn_err == []


def test_no_ID_column_fails(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"idZ","name","paper_number"\n')
            f.write('12345678,"Doe",3\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        with raises(ValueError):
            _ = clean_non_canvas_csv(foo)

        success, warn_err = vlad.validate_csv(foo, spec=None)
        expected = [
            {"warn_or_err": "error", "werr_line": 0, "werr_text": "Missing id column"}
        ]
        assert not success
        # check these lists against each other - order not important
        assert len(warn_err) == len(expected)
        for X in expected:
            assert X in warn_err


def test_two_ID_column_fails(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"ID","Name","id","paper_number"\n')
            f.write('12345678,"Doe",98765432,3\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        success, warn_err = vlad.validate_csv(foo, spec=None)
        expected = [
            {
                "warn_or_err": "error",
                "werr_line": 0,
                "werr_text": "Cannot have multiple id columns",
            }
        ]
        assert not success
        # check these lists against each other - order not important
        assert len(warn_err) == len(expected)
        for X in expected:
            assert X in warn_err


def test_no_name_column_fails(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","studentZZZ","paper_number"\n')
            f.write('12345678,"Doe",7\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        with raises(ValueError):
            _ = clean_non_canvas_csv(foo)

        success, warn_err = vlad.validate_csv(foo, spec=None)
        expected = [
            {"warn_or_err": "error", "werr_line": 0, "werr_text": "Missing name column"}
        ]
        assert not success
        # check these lists against each other - order not important
        assert len(warn_err) == len(expected)
        for X in expected:
            assert X in warn_err


def test_two_name_column_fails(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"ID","name","Name","paper_number"\n')
            f.write('12345678,"Doe","John",7\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        success, warn_err = vlad.validate_csv(foo, spec=None)
        expected = [
            {
                "warn_or_err": "error",
                "werr_line": 0,
                "werr_text": "Cannot have multiple name columns",
            }
        ]
        assert not success
        # check these lists against each other - order not important
        assert len(warn_err) == len(expected)
        for X in expected:
            assert X in warn_err


def test_two_papernumber_column_fails(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"ID","name","paper_number","PAper_NUmber"\n')
            f.write('12345678,"Doe,John",7,3\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        success, warn_err = vlad.validate_csv(foo, spec=None)
        expected = [
            {
                "warn_or_err": "error",
                "werr_line": 0,
                "werr_text": "Cannot have multiple paper number columns",
            }
        ]
        assert not success
        # check these lists against each other - order not important
        assert len(warn_err) == len(expected)
        for X in expected:
            assert X in warn_err


def test_casefold_column_names1(tmpdir):
    # for #1140
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"ID","name","paper_number"\n')
            f.write('12345677,"Doe, Ursula",3\n')
            f.write('12345678,"Doe, Carol",4\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert "id" in df.columns
        assert "name" in df.columns
        assert set(df.columns) == set(("id", "name", "paper_number"))
        success, warn_err = vlad.validate_csv(foo, spec=None)
        assert success
        assert warn_err == []


def test_casefold_column_names2(tmpdir):
    # for #1140
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","NaMe","paper_number"\n')
            f.write('12345678,"Doe",3\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert "id" in df.columns
        assert "name" in df.columns
        assert set(df.columns) == set(("id", "name", "paper_number"))
        success, warn_err = vlad.validate_csv(foo, spec=None)
        assert success
        assert warn_err == []


def test_casefold_column_names3(tmpdir):
    # for #1140
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name","Paper_NUMber"\n')
            f.write('12345678,"Doe",3\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert "id" in df.columns
        assert "name" in df.columns
        assert set(df.columns) == set(("id", "name", "paper_number"))
        success, warn_err = vlad.validate_csv(foo, spec=None)
        assert success
        assert warn_err == []


def test_missing_student_info(tmpdir):
    # testing for #1314
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name","paper_number","hungry"\n')
            f.write('12345677,"Doe, Ursula",3,"yes"\n')
            f.write('87654322,"",4,"who knows"\n')
            f.write('87654323,"A",5,"who knows"\n')
            f.write(',"Doe, John",6,"who knows"\n')
            f.write('"x","Doe, Jan",8,"who knows"\n')
            f.write('12345678,"Doe, Bob",,"yes"\n')

        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert set(df.columns) == set(("id", "name", "paper_number"))
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
            f.write('"id","name","paper_number"\n')
            f.write('12345678,"Doe",1\n')
            f.write('12345679,"Doer",2\n')
            f.write('12345680,"Doerr",3\n')
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
            f.write('"ID","name","paper_number"\n')
            f.write('12345677,"D",1\n')
            f.write('12345678,"",2\n')
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
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name","paper_number"\n')
            f.write('12345677,"Doe, Ursula",1\n')
            f.write('12345678,"Doe, 学生",2\n')
    success, warn_err = vlad.validate_csv(foo)
    assert success
    assert not warn_err


def test_partial_papernumbers(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name","paper_number"\n')
            f.write('12345677,"Doe, Ursula",1\n')
            f.write('12345678,"Doe, Bob",\n')
    success, warn_err = vlad.validate_csv(foo)
    assert success
    assert warn_err == []


def test_repeated_papernumbers(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name","paper_number"\n')
            f.write('12345677,"Doe, Ursula",1\n')
            f.write('12345678,"Doe, Bob",1,\n')
    success, warn_err = vlad.validate_csv(foo)
    assert not success
    expected = [
        {
            "warn_or_err": "error",
            "werr_line": 2,
            "werr_text": "Paper-number '1' is used multiple times - on lines [2, 3]",
        }
    ]
    # check these lists against each other - order not important
    assert len(warn_err) == len(expected)
    for X in expected:
        assert X in warn_err
