#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2019-2020 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Dryden Wiebe

import csv
import os
import sys
import tempfile

import pkg_resources
import pandas

from ..finish.return_tools import import_canvas_csv


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


def clean_non_canvas_csv(csv_file_name):
    """Read the csv file and clean the csv file.

    1. Retrieve the id.
    2. Retrieve the studentName is preset.
    3. If not, retrieve student given name and surname in the document.

    You may want to check first with `check_is_non_canvas_csv`.

    Arguments:
        csv_file_name {Str} -- Name of the csv file.

    Returns:
        pandas.core.frame.DataFrame -- Dataframe object returned with columns id and studentName.
    """

    student_info_df = pandas.read_csv(csv_file_name, dtype="object")
    print('Extracting columns from csv file: "{0}"'.format(csv_file_name))

    # strip excess whitespace from column names
    student_info_df.rename(columns=lambda x: x.strip(), inplace=True)

    # now check we have the columns needed
    if "id" in student_info_df.columns:
        print('"id" column present')
        # strip excess whitespace
        student_info_df["id"] = student_info_df["id"].apply(lambda X: X.strip())

    # if we have fullname then we are good to go.
    if "studentName" in student_info_df.columns:
        print('"studentName" column present')
        student_info_df["studentName"].apply(lambda X: X.strip())
        return student_info_df

    # Otherwise, we will check the titles again
    # we need one of some approx of last-name field
    firstname_column_title = None
    for column_title in student_info_df.columns:
        if column_title.casefold() in (x.casefold() for x in possible_surname_fields):
            print('"{}" column present'.format(column_title))
            firstname_column_title = column_title
            break
    # strip the excess whitespace
    student_info_df[firstname_column_title] = student_info_df[
        firstname_column_title
    ].apply(lambda X: X.strip())

    # we need one of some approx of given-name field
    lastname_column_title = None
    for column_title in student_info_df.columns:
        if column_title.casefold() in (
            x.casefold() for x in possible_given_name_fields
        ):
            print('"{}" column present'.format(column_title))
            lastname_column_title = column_title
            break
    # strip the excess whitespace
    student_info_df[lastname_column_title] = student_info_df[
        lastname_column_title
    ].apply(lambda X: X.strip())

    # concat firstname_column_title and lastname_column_title fields into fullName field
    # strip excess whitespace from those fields
    student_info_df["studentName"] = (
        student_info_df[firstname_column_title]
        + ", "
        + student_info_df[lastname_column_title]
    )

    student_info_df.columns = ["id", "studentName"]

    return student_info_df


def check_is_non_canvas_csv(csv_file_name):
    """Read the csv file and check to see if the id and student name exist.

    1. Check if id is present.
    2. Check if studentName is preset.
    3. If not, check for given name and surname in the document.

    Arguments:
        csv_file_name {Str} -- Name of the csv file.

    Returns:
        bool -- True/False
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
        csv_file_name {Str} -- Name of the csv file.

    Returns:
        pandas.core.frame.DataFrame -- Dataframe object returned with columns id and studentName.
    """
    student_info_df = import_canvas_csv(csv_file_name)
    student_info_df = student_info_df[["Student Number", "Student"]]
    student_info_df.columns = ["id", "studentName"]
    return student_info_df


def check_is_canvas_csv(csv_file_name):
    """Checks to see if a function is a canvas style csv file.

    Arguments:
        csv_file_name {Str} -- Name of the csv file.

    Returns:
        boolean -- True/False
    """
    with open(csv_file_name) as csvfile:
        csv_reader = csv.DictReader(csvfile, skipinitialspace=True)
        csv_fields = csv_reader.fieldnames
    return all(x in csv_fields for x in canvas_columns_format)


def check_latin_names(student_info_df):
    """Pass the pandas object and check studentNames encode to Latin-1.

    Prints out a warning message for any that are not encodable.

    Arguments:
        student_info_df {pandas.core.frame.DataFrame} -- Dataframe object returned with columns id and studentName.

    Returns:
        bool -- True/False
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
    3. Otherwise exit(1).  TODO: library calls shouldn't do this!
    4. Check for latin character encodability, a restriction to be
       loosened in the future.

    Arguments:
        student_csv_file_name (str): Name of the class info csv file.

    Return:
        pandas dataframe: the processed classlist data.
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
    # Otherwise we have an error
    else:
        print("Problems with the classlist you supplied. See output above.")
        sys.exit(1)

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


def process_class_list(student_csv_file_name, demo=False):
    """Get student names/IDs from a csv file.

    Student numbers come from an `id` column.  There is some
    flexibility about student names: most straightforward is a
    second column named `studentNames`.  If that isn't present,
    try to construct a name from surname, given name, guessing
    column names from the following lists:

      - :func:`plom.produce.possible_surname_fields`
      - :func:`plom.produce.possible_given_name_fields`

    Alternatively, give a .csv exported from Canvas (experimental!)

    Arguments:
        student_csv_file_name (str): Name of the class info csv file.

    Keyword Arguments:
        demo (bool): if `True`, the filename is ignored and we use demo
            data (default: `False`).

    Return:
        dict: keys are student IDs (str), values are student names (str).
    """
    if demo:
        print("Using demo classlist - DO NOT DO THIS FOR A REAL TEST")
        cl = pkg_resources.resource_string("plom", "demoClassList.csv")
        # this is dumb, make it work right out of the string/bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as f:
            with open(f.name, "wb") as fh:
                fh.write(cl)
            return process_class_list(f.name)
        # from io import StringIO, BytesIO
        # student_csv_file_name = BytesIO(cl)

    if not student_csv_file_name:
        print("Please provide a classlist file: see help")
        sys.exit(1)

    if not os.path.isfile(student_csv_file_name):
        print('Cannot find file "{}"'.format(student_csv_file_name))
        sys.exit(1)
    df = process_classlist_backend(student_csv_file_name)
    # order is important, leave it as a list
    return list(zip(df.id, df.studentName))
