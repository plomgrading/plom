# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2024 Colin B. Macdonald
# Copyright (C) 2022-2024 Andrew Rechnitzer

from pytest import raises
from pathlib import Path

from plom import SpecVerifier

from .classlistValidator import PlomClasslistValidator
from .buildClasslist import clean_non_canvas_csv
from ..misc_utils import working_directory


def test_ok_to_contain_unused_column_names(tmpdir) -> None:
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


def test_no_ID_column_fails(tmpdir) -> None:
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
        assert not success
        assert len(warn_err) == 1
        assert warn_err[0]["warn_or_err"] == "error"
        assert warn_err[0]["werr_line"] == 0
        assert warn_err[0]["werr_text"].startswith("Missing 'id' column")


def test_two_ID_column_fails(tmpdir) -> None:
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


def test_no_name_column_fails(tmpdir) -> None:
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
        assert not success
        assert len(warn_err) == 1
        assert warn_err[0]["warn_or_err"] == "error"
        assert warn_err[0]["werr_line"] == 0
        assert warn_err[0]["werr_text"].startswith("Missing 'name' column")


def test_two_name_column_fails(tmpdir) -> None:
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


def test_two_papernumber_column_fails(tmpdir) -> None:
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


def test_casefold_column_names1(tmpdir) -> None:
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


def test_casefold_column_names2(tmpdir) -> None:
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


def test_casefold_column_names3(tmpdir) -> None:
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


def test_missing_student_info(tmpdir) -> None:
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
                "werr_text": "SID is blank, SID  has incorrect length - expecting 8 digits",
            },
            {
                "warn_or_err": "error",
                "werr_line": 6,
                "werr_text": "SID 'x' is not an integer, SID x has incorrect length - expecting 8 digits",
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


def test_check_classlist_length(tmpdir) -> None:
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


def test_short_name_warning1(tmpdir) -> None:
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


def test_non_latin_name(tmpdir) -> None:
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


def test_partial_papernumbers(tmpdir) -> None:
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


def test_repeated_papernumbers(tmpdir) -> None:
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


def test_sentinel_papernumbers(tmpdir) -> None:
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name","paper_number"\n')
            f.write('12345677,"Doe, Ursula",1\n')
            f.write('12345678,"Doe, Bob",\n')
            f.write('12345679,"Doe, Bobby",-1\n')
    success, warn_err = vlad.validate_csv(foo)
    assert success
    assert warn_err == []


def test_bad_papernumbers(tmpdir) -> None:
    tmpdir = Path(tmpdir)
    vlad = PlomClasslistValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name","paper_number"\n')
            f.write('12345677,"Doe, Ursula",1\n')
            f.write('12345678,"Doe, Bob",1.1\n')
            f.write('12345679,"Doe, Bobby",-17\n')
            f.write('12345680,"Doe, Rob",-17.3\n')
            f.write('12345681,"Doe, Robby",-7.0\n')
            f.write('12345682,"Doe, Bobbert",7.0\n')
    success, warn_err = vlad.validate_csv(foo)
    assert not success
    expected = [
        {
            "warn_or_err": "error",
            "werr_line": 3,
            "werr_text": "Paper-number 1.1 is not a non-negative integer",
        },
        {
            "warn_or_err": "error",
            "werr_line": 4,
            "werr_text": "Paper-number -17 must be a non-negative integer, or blank or '-1' to indicate 'do not prename'",
        },
        {
            "warn_or_err": "error",
            "werr_line": 5,
            "werr_text": "Paper-number -17.3 is not a non-negative integer",
        },
        {
            "warn_or_err": "error",
            "werr_line": 6,
            "werr_text": "Paper-number -7.0 is not a non-negative integer",
        },
        {
            "warn_or_err": "error",
            "werr_line": 7,
            "werr_text": "Paper-number 7.0 is nearly, but not quite, a non-negative integer",
        },
    ]
    assert len(warn_err) == len(expected)
    for X in expected:
        assert X in warn_err


def test_leading_zero_sid(tmp_path) -> None:
    vlad = PlomClasslistValidator()
    foo = tmp_path / "foo.csv"
    with open(foo, "w") as f:
        f.write('"ID","name","paper_number"\n')
        f.write('12345677,"Doe, Ursula",\n')
        f.write('00123400,"Doe, Carol",\n')
        f.write('12345678,"Doe, Max",\n')
    assert vlad.check_is_non_canvas_csv(foo)
    df = clean_non_canvas_csv(foo)
    assert "id" in df.columns
    success, warn_err = vlad.validate_csv(foo, spec=None)
    assert success
    assert warn_err == []
    # and 00123400 still in there!
    d = df["id"].to_dict()
    assert "00123400" in d.values()
