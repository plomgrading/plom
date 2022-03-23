# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021-2022 Colin B. Macdonald

from pytest import raises
from pathlib import Path

from .classlistValidator import PlomCLValidator
from .buildClasslist import clean_non_canvas_csv
from ..misc_utils import working_directory


def test_multi_column_names(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","Surname","preferredName"\n')
            f.write('12345677,"Doe","Ursula"\n')
            f.write('12345678,"Doe","Carol"\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert "id" in df.columns
        assert "studentName" in df.columns
        assert set(df.columns) == set(("id", "studentName"))


def test_ok_to_contain_unused_column_names(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","Surname","preferredName","hungry"\n')
            f.write('12345677,"Doe","Ursula","yes"\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert set(df.columns) == set(("id", "studentName"))


def test_only_one_name_column(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","name"\n')
            f.write('12345678,"Doe"\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        with raises(ValueError):
            _ = clean_non_canvas_csv(foo)


def test_no_ID_column_fails(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"idZ","studentName"\n')
            f.write('12345678,"Doe"\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        with raises(ValueError):
            _ = clean_non_canvas_csv(foo)


def test_casefold_column_names1(tmpdir):
    # for #1140
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"ID","surNaMe","preFeRRedname"\n')
            f.write('12345677,"Doe","Ursula"\n')
            f.write('12345678,"Doe","Carol"\n')
        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert "id" in df.columns
        assert "studentName" in df.columns
        assert set(df.columns) == set(("id", "studentName"))


def test_casefold_column_names2(tmpdir):
    # for #1140
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"Id","StuDentNamE"\n')
            f.write('12345678,"Doe"\n')
        assert not vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert "id" in df.columns
        assert "studentName" in df.columns
        assert set(df.columns) == set(("id", "studentName"))


def test_missing_student_info1(tmpdir):
    # testing for #1314
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","studentName","hungry"\n')
            f.write('12345677,"Doe, Ursula","yes"\n')
            f.write('87654322,"","who knows"\n')
            f.write(',"Doe, John","who knows"\n')
            f.write('"x","Doe, Jan","who knows"\n')

        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        print(">>>>> ", df.columns)
        assert set(df.columns) == set(("id", "studentName"))
        success, warn_err = vlad.validate_csv(foo, spec=None)
        print(f"Found errors = {success}, {warn_err}")
        assert not success
        # should see errors on lies 3,4,5
        # [
        # {'warn_or_err': 'error', 'werr_line': 3, 'werr_text': 'Missing name'},
        # {'warn_or_err': 'error', 'werr_line': 4, 'werr_text': "SID '' is not an integer, "}
        # {'warn_or_err': 'error', 'werr_line': 5, 'werr_text': "SID 'x' is not an integer, "}
        # ]
        where_errors = sorted([x["werr_line"] for x in warn_err])
        assert where_errors == [3, 4, 5]


def test_missing_student_info2(tmpdir):
    # testing for #1314
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","surname","preferredName","hungry"\n')
            f.write('12345677,"Doe","Ursula","yes"\n')
            f.write('87654321,"Doe","","who knows"\n')
            f.write('87654322,"","John","who knows"\n')
            f.write(',"Doe","John","who knows"\n')
            f.write('"x","Doe", "Jan", "who knows"\n')

        assert vlad.check_is_non_canvas_csv(foo)
        df = clean_non_canvas_csv(foo)
        assert set(df.columns) == set(("id", "studentName"))
        success, warn_err = vlad.validate_csv(foo, spec=None)
        print(f"Found errors = {success}, {warn_err}")
        assert not success
        # should see errors on lies 3,4,5,6
        # [
        # {'warn_or_err': 'error', 'werr_line': 3, 'werr_text': 'Missing given name'},
        # {'warn_or_err': 'error', 'werr_line': 4, 'werr_text': 'Missing surname'},
        # {'warn_or_err': 'error', 'werr_line': 5, 'werr_text': 'SID '' is not an integer, '}
        # {'warn_or_err': 'error', 'werr_line': 6, 'werr_text': "SID 'x' is not an integer, "}
        # ]
        where_errors = sorted([x["werr_line"] for x in warn_err])
        assert where_errors == [3, 4, 5, 6]


def test_check_classlist_length1(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    from plom import SpecVerifier

    spec = SpecVerifier.demo(num_to_produce=2)

    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","studentName"\n')
            f.write('12345678,"Doe"\n')
            f.write('12345679,"Doer"\n')
            f.write('12345680,"Doerr"\n')
        success, warn_err = vlad.validate_csv(foo, spec=spec)
        # should get
        # {'warn_or_err': 'warning', 'werr_line': 0, 'werr_text': 'Classlist is long. Classlist contains 3 names, but spec:numberToProduce is 2'}
        assert success
        assert warn_err[0]["werr_line"] == 0
        assert (
            warn_err[0]["werr_text"]
            == "Classlist is long. Classlist contains 3 names, but spec:numberToProduce is 2"
        )


def test_check_classlist_length2(tmpdir):
    tmpdir = Path(tmpdir)
    vlad = PlomCLValidator()
    from plom import SpecVerifier

    spec = SpecVerifier.demo(num_to_produce=3)
    # manually set number to name longer than classlist
    spec.spec["numberToName"] = 5

    with working_directory(tmpdir):
        foo = tmpdir / "foo.csv"
        with open(foo, "w") as f:
            f.write('"id","studentName"\n')
            f.write('12345678,"Doe"\n')
            f.write('12345679,"Doer"\n')
            f.write('12345680,"Doerr"\n')
        success, warn_err = vlad.validate_csv(foo, spec=spec)
        print(success, warn_err)
        # should get
        # [{'warn_or_err': 'error', 'werr_line': 0, 'werr_text': 'Classlist too short. Classlist contains 3 names, but spec:numberToName is 5'}]
        assert not success
        assert warn_err[0]["werr_line"] == 0
        assert (
            warn_err[0]["werr_text"]
            == "Classlist too short. Classlist contains 3 names, but spec:numberToName is 5"
        )
