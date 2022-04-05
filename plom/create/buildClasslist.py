# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe

import csv
import importlib.resources as resources
from pathlib import Path
import tempfile

import pandas

import plom
from plom.finish.return_tools import import_canvas_csv

from plom.create.classlistValidator import (
    possible_sid_fields,
    possible_one_name_fields,
    possible_given_name_fields,
    possible_surname_fields,
    PlomClasslistValidator,
)

# Note: file is full of pandas warnings, which I think are false positives
# pylint: disable=unsubscriptable-object
# pylint: disable=unsupported-assignment-operation


def clean_non_canvas_csv(csv_file_name, minimalist=True):
    """Read the csv file and clean the csv file.

    1. Retrieve the id.
    2. Retrieve the studentName is preset.
    3. If not, retrieve student given name and surname in the document.

    You may want to check first with `check_is_non_canvas_csv`.

    Arguments:
        csv_file_name (pathlib.Path/str): the csv file.

    Returns:
        pandas.DataFrame: data with columns `id` and `studentName`
        and possibly `papernum` if you had such a column in the input.
        With ``minimalist=True`` kwarg specified, this is all you get,
        otherwise the original columns will be included too, except
        those renamed to create the required columns.
    """
    df = pandas.read_csv(csv_file_name, dtype="object")
    print('Extracting columns from csv file: "{0}"'.format(csv_file_name))

    # strip excess whitespace from column names
    df.rename(columns=lambda x: str(x).strip(), inplace=True)

    # find the id column
    id_column = None
    for c in df.columns:
        if c.casefold() in (x.casefold() for x in possible_sid_fields):
            # print(f'"{c}" column present')
            id_column = c
            break
    if id_column is None:
        # note that this should be caught by the validator
        raise ValueError('no "id" column is present')
    # make sure id column named 'id' - lowercase
    print(f"Renaming column {id_column} to 'id'")
    df.rename(columns={id_column: "id"}, inplace=True)
    # clean up the column - strip whitespace
    df["id"] = df["id"].apply(lambda X: str(X).strip())  # avoid issues with non-string
    # print('"id" column present')
    papernum_column = None
    for c in df.columns:
        if c.casefold() == "papernum":
            print(f'"{c}" column present')
            papernum_column = c
            break
    if papernum_column:
        # JSON + NaN :-( so use negatives for missing: TODO do better?
        df[papernum_column] = df[papernum_column].apply(
            lambda x: -1 if pandas.isna(x) else int(x)
        )
        df.rename(columns={papernum_column: "papernum"}, inplace=True)
        return_columns = ["id", "studentName", "papernum"]
    else:
        return_columns = ["id", "studentName"]

    # see if there is a single name column
    one_name_column = None
    for c in df.columns:
        if c.casefold() in (x.casefold() for x in possible_one_name_fields):
            # print(f'"{c}" column present')
            one_name_column = c
            break
    if one_name_column is not None:
        # make sure id column named 'id' - lowercase
        print(f"Renaming column {one_name_column} to 'studentName'")
        df.rename(columns={one_name_column: "studentName"}, inplace=True)
        # clean up the column - strip whitespace
        df["studentName"].apply(lambda X: str(X).strip())  # avoid errors with blanks
        # print('"studentName" column present')
        if minimalist:
            return df[return_columns]
        return df

    # Otherwise, we will check the column headers again taking the first
    # columns that looks like firstname and a lastname fields
    firstname_column = None
    lastname_column = None
    for c in df.columns:
        if c.casefold() in (x.casefold() for x in possible_surname_fields):
            # print(f'"{c}" column present')
            firstname_column = c
            break
    for c in df.columns:
        if c.casefold() in (x.casefold() for x in possible_given_name_fields):
            # print(f'"{c}" column present')
            lastname_column = c
            break

    if lastname_column is None or firstname_column is None:
        raise ValueError("Cannot find appropriate column titles for names")

    # strip excess whitespace
    df[firstname_column] = df[firstname_column].apply(lambda X: str(X).strip())
    df[lastname_column] = df[lastname_column].apply(lambda X: str(X).strip())

    # concat columns to our preferred column
    df["studentName"] = df[firstname_column] + ", " + df[lastname_column]

    if minimalist:
        return df[return_columns]
    return df


def clean_canvas_csv(csv_file_name):
    """Read the canvas csv file and clean the csv file.

    You may want to first check if the file is a Canvas-exported file
    using `check_is_canvas_csv`.

    Arguments:
        csv_file_name (pathlib.Path/str): the csv file.

    Returns:
        pandas.DataFrame: data with columns `id` and `studentName`
    """
    student_info_df = import_canvas_csv(csv_file_name)
    student_info_df = student_info_df[["Student Number", "Student"]]
    student_info_df.columns = ["id", "studentName"]
    return student_info_df


def process_classlist_backend(student_csv_file_name):
    """Process classlist, either from a canvas style csv or user-formatted.

    1. Check if the file is a csv exported from Canvas.  If so extract
       relevant headers and clean-up the file.
    2. Otherwise check for suitable ID and name columns.
    3. Check for latin character encodability, a restriction to be
       loosened in the future.

    Arguments:
        student_csv_file_name (pathlib.Path/str): class info csv file.

    Return:
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


def print_classlist_warnings_errors(warn_err):
    # separate into warn and err
    warn = [X for X in warn_err if X["warn_or_err"] == "warning"]
    err = [X for X in warn_err if X["warn_or_err"] != "warning"]
    # sort by line number
    warn.sort(key=lambda X: X["werr_line"])
    err.sort(key=lambda X: X["werr_line"])

    if warn:
        print("Classlist validation warnings:")
        for X in warn:
            print(f"\tline {X['werr_line']}: {X['werr_text']}")
    if err:
        print("Classlist validation errors:")
        for X in err:
            print(f"\tline {X['werr_line']}: {X['werr_text']}")


def get_demo_classlist(spec):
    """Get the demo classlist."""
    # Direct approach: but maybe I like exercising code-paths with below...
    # with resources.open_binary(plom, "demoClassList.csv") as f:
    #     df = clean_non_canvas_csv(f)
    # classlist = df.to_dict("records")

    b = resources.read_binary(plom, "demoClassList.csv")
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
    return clist


def process_classlist_file(student_csv_file_name, spec, *, ignore_warnings=False):
    """Get student names/IDs from a csv file.

    Student numbers come from an `id` column.  There is some
    flexibility about student names: most straightforward is a
    second column named `studentNames`.  If that isn't present,
    try to construct a name from surname, given name, guessing
    column names from the following lists:

      - :func:`plom.create.possible_surname_fields`
      - :func:`plom.create.possible_given_name_fields`

    Alternatively, give a .csv exported from Canvas (experimental!)

    Arguments:
        student_csv_file_name (pathlib.Path/str): class info csv file.
        spec (dict): validated test spec.

    Keyword Arguments:
        ignore_warnings (bool): if true, proceed with classlist
            processing even if there are warnings.  Default False.

    Return: tuple: if successful then "(True, clist)" where clist is a
        list of dicts each with "id" and "studentName". On failure
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
    success, warn_err = vlad.validate_csv(student_csv_file_name, spec=spec)

    if success is False:
        # validation failed, return warning, error list
        PlomClasslistValidator.print_classlist_warnings_errors(warn_err)
        return (False, warn_err)

    # validation passed but there are warnings
    if warn_err:
        print_classlist_warnings_errors(warn_err)
        if ignore_warnings:
            print("Continuing despite warnings")
        else:
            return (False, warn_err)

    df = process_classlist_backend(student_csv_file_name)
    # "records" makes it output a list-of-dicts, one per row
    return (True, df.to_dict("records"))
