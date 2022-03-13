# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe

import csv
from pathlib import Path
import sys
import tempfile

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import pandas

import plom
from plom.finish.return_tools import import_canvas_csv


possible_surname_fields = ["surname", "familyName", "lastName"]

possible_given_name_fields = [
    "name",
    "givenName",
    "firstName",
    "givenNames",
    "firstNames",
    "preferredName",
    "preferredNames",
    "nickName",
    "nickNames",
]

canvas_columns_format = ("Student", "ID", "SIS User ID", "SIS Login ID")


# Note: file is full of pandas warnings, which I think are false positives
# pylint: disable=unsubscriptable-object
# pylint: disable=unsupported-assignment-operation


def clean_non_canvas_csv(csv_file_name):
    """Read the csv file and clean the csv file.

    1. Retrieve the id.
    2. Retrieve the studentName is preset.
    3. If not, retrieve student given name and surname in the document.

    You may want to check first with `check_is_non_canvas_csv`.

    Arguments:
        csv_file_name (pathlib.Path/str): the csv file.

    Returns:
        pandas.DataFrame: data with columns `id` and `studentName`.
    """
    df = pandas.read_csv(csv_file_name, dtype="object")
    print('Extracting columns from csv file: "{0}"'.format(csv_file_name))

    # strip excess whitespace from column names
    df.rename(columns=lambda x: x.strip(), inplace=True)

    if "id" not in df.columns:
        raise ValueError('no "id" column is present')
    print('"id" column present')
    # strip excess whitespace
    df["id"] = df["id"].apply(lambda X: X.strip())

    # see if we have our preferred format for a name column
    if "studentName" in df.columns:
        print('"studentName" column present')
        df["studentName"].apply(lambda X: X.strip())
        return df

    # Otherwise, we will check the column headers again taking the first
    # columns that looks like firstname and a lastname fields
    firstname_column = None
    lastname_column = None
    for c in df.columns:
        if c.casefold() in (x.casefold() for x in possible_surname_fields):
            print(f'"{c}" column present')
            firstname_column = c
            break
    for c in df.columns:
        if c.casefold() in (x.casefold() for x in possible_given_name_fields):
            print(f'"{c}" column present')
            lastname_column = c
            break

    if lastname_column is None or firstname_column is None:
        raise ValueError("Cannot find appropriate column titles for names")

    # strip excess whitespace
    df[firstname_column] = df[firstname_column].apply(lambda X: X.strip())
    df[lastname_column] = df[lastname_column].apply(lambda X: X.strip())

    # concat columns to our preferred column
    df["studentName"] = df[firstname_column] + ", " + df[lastname_column]

    # just return the two relevant columns
    return df[["id", "studentName"]]


def check_is_non_canvas_csv(csv_file_name):
    """Read the csv file and check if id and appropriate student name exist.

    1. Check if id is present.
    2. Check if studentName is preset.
    3. If not, check for given name and surname in the document.

    Arguments:
        csv_file_name (pathlib.Path/str): the csv file.

    Returns:
        bool
    """

    student_info_df = pandas.read_csv(csv_file_name, dtype="object")
    print('Loading from non-Canvas csv file to check file: "{0}"'.format(csv_file_name))

    # strip excess whitespace from column names
    student_info_df.rename(columns=lambda x: x.strip(), inplace=True)

    if "id" not in student_info_df.columns:
        print('Cannot find "id" column')
        print("Columns present = {}".format(student_info_df.columns))
        return False

    # if we have don't have  then we are good to go.
    if "studentName" not in student_info_df.columns:

        # we need one of some approx of last-name field
        firstname_column_title = None
        for column_title in student_info_df.columns:
            if column_title.casefold() in (
                x.casefold() for x in possible_surname_fields
            ):
                print('"{}" column present'.format(column_title))
                firstname_column_title = column_title
                break
        if firstname_column_title is None:
            print(
                'Cannot find column to use for "surname", tried: {}'.format(
                    ", ".join(possible_surname_fields)
                )
            )
            print("Columns present = {}".format(student_info_df.columns))
            return False

        # we need one of some approx of given-name field
        lastname_column_title = None
        for column_title in student_info_df.columns:
            if column_title.casefold() in (
                x.casefold() for x in possible_given_name_fields
            ):
                print('"{}" column present'.format(column_title))
                lastname_column_title = column_title
                break
        if lastname_column_title is None:
            print(
                'Cannot find column to use for "given name", tried: {}'.format(
                    ", ".join(possible_given_name_fields)
                )
            )
            print("Columns present = {}".format(student_info_df.columns))
            return False

    return True


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


def check_is_canvas_csv(csv_file_name):
    """Detect if a csv file is likely a Canvas-exported classlist.

    Arguments:
        csv_file_name (pathlib.Path/str): csv file to be checked.

    Returns:
        bool: True if we think the input was from Canvas, based on
            presence of certain header names.  Otherwise False.
    """
    with open(csv_file_name) as csvfile:
        csv_reader = csv.DictReader(csvfile, skipinitialspace=True)
        csv_fields = csv_reader.fieldnames
    return all(x in csv_fields for x in canvas_columns_format)


def check_latin_names(student_info_df):
    """Check if a dataframe has "studentName"s that encode to Latin-1.

    Prints out a warning message for any that are not encodable.

    Arguments:
        student_info_df (pandas.DataFrame): with at least columns `id`
            and `studentName`.

    Returns:
        bool: False if one or more names contain non-Latin characters.
    """
    # TODO - make this less eurocentric in the future.
    encoding_problems = []
    for index, row in student_info_df.iterrows():
        try:
            tmp = row["studentName"].encode("Latin-1")
        except UnicodeEncodeError:
            encoding_problems.append(
                'row {}, number {}, name: "{}"'.format(
                    index, row["id"], row["studentName"]
                )
            )

    if len(encoding_problems) > 0:
        print("WARNING: The following ID/name pairs contain non-Latin characters:")
        for problem in encoding_problems:
            print(problem)
        return False
    else:
        return True


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

    # First we check if this csv file is a Canvas output
    if check_is_canvas_csv(student_csv_file_name):
        print("This file looks like it was exported from Canvas")
        student_info_df = clean_canvas_csv(student_csv_file_name)
        print("We have successfully extracted columns from Canvas data and renaming")
    elif check_is_non_canvas_csv(student_csv_file_name):
        print(
            "This file looks like it was not exported from Canvas; checking for the required information..."
        )
        student_info_df = clean_non_canvas_csv(student_csv_file_name)
        print(
            "We have successfully extracted and renamed columns from the non Canvas data."
        )
    else:
        raise ValueError("Problems with the supplied classlist. See output above.")

    # Check characters in names are latin-1 compatible
    if not check_latin_names(student_info_df):
        print(">>> WARNING <<<")
        print(
            "Potential classlist problems",
            "The classlist you supplied contains non-Latin characters - see console output above. "
            "You can proceed, but it might cause problems later. "
            "Apologies for the eurocentricity.",
        )

    # print("Saving to {}".format(outputfile))
    # df.to_csv(outputfile, index=False)
    return student_info_df


def get_demo_classlist():
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
    C = process_classlist_file(f)
    f.unlink()
    return C


def process_classlist_file(student_csv_file_name):
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

    Keyword Arguments:
        demo (bool): if `True`, the filename is ignored and we use demo
            data (default: `False`).

    Return:
        list: A list of dicts, each with `"id"` and `"studentName"`.
    """
    student_csv_file_name = Path(student_csv_file_name)
    if not student_csv_file_name.exists():
        raise FileNotFoundError(f'Cannot find file "{student_csv_file_name}"')
    df = process_classlist_backend(student_csv_file_name)
    # "records" makes it output a list-of-dicts, one per row
    return df.to_dict("records")
