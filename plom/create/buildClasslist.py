# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2019-2024 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe

import csv
from pathlib import Path
import sys
import tempfile

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources

# try to avoid importing Pandas unless we use specific functions: Issue #2154
# import pandas

import plom
from plom.finish.return_tools import import_canvas_csv

from plom.create.classlistValidator import (
    sid_field,
    fullname_field,
    papernumber_field,
    PlomClasslistValidator,
)

# Note: file is full of pandas warnings, which I think are false positives
# pylint: disable=unsubscriptable-object
# pylint: disable=unsupported-assignment-operation


def clean_non_canvas_csv(csv_file_name, minimalist=True):
    """Read the csv file and clean the csv file.

    1. Retrieve the id.
    2. Retrieve the name

    You may want to check first with `check_is_non_canvas_csv`.

    Args:
        csv_file_name (pathlib.Path/str): the csv file.

    Keyword Args:
        minimalist: discard unnecessary columns.

    Returns:
        pandas.DataFrame: data with columns `id` and `name`
        and possibly `papernum` if you had such a column in the input.
        With ``minimalist=True`` kwarg specified, this is all you get,
        otherwise the original columns will be included too, except
        those renamed to create the required columns.
    """
    import pandas

    df = pandas.read_csv(csv_file_name, dtype="object")
    print('Extracting columns from csv file: "{0}"'.format(csv_file_name))

    # strip excess whitespace from column names
    df.rename(columns=lambda x: str(x).strip(), inplace=True)

    # find the id column and clean it up.
    id_column = None
    for c in df.columns:
        if c.casefold() == sid_field:
            id_column = c
            break
    if id_column is None:
        raise ValueError('no "id" column is present')
    if id_column != "id":
        print(f'Renaming column "{id_column}" to "id"')
    df.rename(columns={id_column: "id"}, inplace=True)
    # clean up the column - strip whitespace
    df["id"] = df["id"].apply(lambda X: str(X).strip())  # avoid issues with non-string

    # find the name column and clean it up.
    fullname_column = None
    for c in df.columns:
        if c.casefold() == fullname_field.casefold():
            fullname_column = c
            break
    if fullname_column is None:
        raise ValueError('no "name" column is present')
    if fullname_column != "name":
        print(f'Renaming column "{fullname_column}" to "name"')
    df.rename(columns={fullname_column: "name"}, inplace=True)
    # clean up the column - strip whitespace
    df["name"].apply(lambda X: str(X).strip())  # avoid errors with blanks

    find_paper_number_column(df)

    # everything clean - now either return just the necessary columns or all cols.
    if minimalist:
        return df[["id", "name", "paper_number"]]
    return df


def find_paper_number_column(df, *, make=True):
    """Find or make a paper_number column.

    Args:
        df: a Pandas dataframe.

    Keyword Args:
        make (bool): make an placeholder `paper_number` column if one
            is not found.  True by default.

    Returns:
        None: modifies the input `df`.
    """
    import pandas

    # find the paper-number column and clean it up.
    papernumber_column = None
    for c in df.columns:
        if c.casefold() == papernumber_field.casefold():
            papernumber_column = c
            break
    if not papernumber_column:
        if not make:
            raise ValueError('no "paper_number" column is present.')
        papernumber_column = "paper_number"
        df[[papernumber_column]] = None
    # clean it up.
    df[papernumber_column] = df[papernumber_column].apply(
        lambda x: -1 if pandas.isna(x) else int(x)
    )
    if papernumber_column != "paper_number":
        print(f'Renaming column "{papernumber_column}" to "paper_number"')
    df.rename(columns={papernumber_column: "paper_number"}, inplace=True)


def clean_canvas_csv(csv_file_name):
    """Read the canvas csv file and clean the csv file.

    You may want to first check if the file is a Canvas-exported file
    using `check_is_canvas_csv`.

    Arguments:
        csv_file_name (pathlib.Path/str): the csv file.

    Returns:
        pandas.DataFrame: data with columns `id` and `name`
    """
    STUDENT_NUM_COL = "Student Number"
    # STUDENT_NUM_COL = "SIS User ID"
    df = import_canvas_csv(csv_file_name)
    find_paper_number_column(df)
    df = df[[STUDENT_NUM_COL, "Student", "paper_number"]]
    df.columns = ["id", "name", "paper_number"]
    return df


def process_classlist_backend(student_csv_file_name):
    """Process classlist, either from a canvas style csv or user-formatted.

    1. Check if the file is a csv exported from Canvas.  If so extract
       relevant headers and clean-up the file.
    2. Otherwise check for suitable ID and name columns.
    3. Check for latin character encodability, a restriction to be
       loosened in the future.

    Arguments:
        student_csv_file_name (pathlib.Path/str): class info csv file.

    Returns:
        pandas.DataFrame: the processed classlist data.
    """
    with open(student_csv_file_name) as csvfile:
        csv_reader = csv.DictReader(csvfile, skipinitialspace=True)
        csv_fields = csv_reader.fieldnames
    print("Class list headers = {}".format(csv_fields))

    # Depending on the type of file, whether its a Canvas file or not,
    # we need to check it has the minimum information ie student name/id.
    # If not we will fail the process.

    # First we check if this csv file is a Canvas output - using the validator

    vlad = PlomClasslistValidator()

    if vlad.check_is_canvas_csv(student_csv_file_name):
        print("This file looks like it was exported from Canvas")
        student_info_df = clean_canvas_csv(student_csv_file_name)
        print("We have successfully extracted columns from Canvas data and renaming")
    elif vlad.check_is_non_canvas_csv(student_csv_file_name):
        print(
            "This file looks like it was not exported from Canvas; checking for the required information..."
        )
        student_info_df = clean_non_canvas_csv(student_csv_file_name)
        print(
            "We have successfully extracted and renamed columns from the non Canvas data."
        )
    else:
        raise ValueError("Problems with the supplied classlist. See output above.")

    return student_info_df


def get_demo_classlist(spec):
    """Get the demo classlist."""
    # Direct approach: but maybe I like exercising code-paths with below...
    # with (resources.files(plom) / "demoClassList.csv").open("r") as f:
    #     df = clean_non_canvas_csv(f)
    # classlist = df.to_dict("records")

    b = (resources.files(plom) / "demoClassList.csv").read_bytes()
    # Context manager not appropriate here, Issue #1996
    f = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name)
    with open(f, "wb") as fh:
        fh.write(b)

    success, clist = process_classlist_file(f, spec, ignore_warnings=True)

    if success is False:
        raise ValueError(
            f"Something has gone seriously wrong with the demo classlist - {clist}."
        )

    f.unlink()

    # The raw demo classlist does not have any pre-named students.
    # So here we pre-name half of spec[numberToProduce] papers
    for n in range(spec["numberToProduce"] // 2):
        clist[n]["paper_number"] = n + 1
    # now only return the classlist truncated to numberToProduce lines
    return clist[: (spec["numberToProduce"] + 1)]


def process_classlist_file(student_csv_file_name, spec, *, ignore_warnings=False):
    """Get student names/IDs from a csv file.

    Student numbers come from an `id` column. Student names
    must be in a *single* 'name' column. There is some flexibility
    in those titles, see

    - :func:`plom.create.possible_sid_fields`
    - :func:`plom.create.possible_fullname_fields`

    Alternatively, give a .csv exported from Canvas (experimental!)

    Arguments:
        student_csv_file_name (pathlib.Path/str): class info csv file.
        spec (dict): validated test spec.

    Keyword Arguments:
        ignore_warnings (bool): if true, proceed with classlist
            processing even if there are warnings.  Default False.

    Returns:
        tuple: if successful then "(True, clist)" where clist is a
        list of dicts each with "id" and "name". On failure
        "(False, warn_err)" where "warn_err" is a list of dicts of
        warnings and errors. Each dict contains "warn_or_err" which is
        'warning' or 'error', "werr_line" being the line number at
        which the error occurs, and 'werr_text' being a string
        describing the warning/error.
    """
    student_csv_file_name = Path(student_csv_file_name)
    if not student_csv_file_name.exists():
        raise FileNotFoundError(f'Cannot find file "{student_csv_file_name}"')

    vlad = PlomClasslistValidator()

    if not vlad.check_is_canvas_csv(student_csv_file_name):
        success, warn_err = vlad.validate_csv(student_csv_file_name, spec=spec)

        if success is False:
            # validation failed, return warning, error list
            PlomClasslistValidator.print_classlist_warnings_errors(warn_err)
            return (False, warn_err)

        # validation passed but there are warnings
        if warn_err:
            PlomClasslistValidator.print_classlist_warnings_errors(warn_err)
            if not ignore_warnings:
                return (False, warn_err)
            print("Continuing despite warnings")

    df = process_classlist_backend(student_csv_file_name)
    # "records" makes it output a list-of-dicts, one per row
    return (True, df.to_dict("records"))
