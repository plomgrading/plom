#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import json
import os
import sys
import subprocess
import pandas

from ..finish.return_tools import import_canvas_csv


def checkNonCanvasCSV(fname):
    """Read in a csv and check it has ID column.

    Must also have either
    (*) studentName column or
    (*) [surname/familyName/lastName] and [name/givenName(s)/preferredName(s)/firstName/nickName(s)] columns
    In the latter case it creates a studentName column
    """
    df = pandas.read_csv(fname, dtype="object")
    print('Loading from non-Canvas csv file: "{0}"'.format(fname))
    # strip excess whitespace from column names
    df.rename(columns=lambda x: x.strip(), inplace=True)

    # now check we have the columns needed
    if "id" in df.columns:
        print('"id" column present')
        # strip excess whitespace
        df["id"] = df["id"].apply(lambda X: X.strip())
    else:
        print('Cannot find "id" column')
        print("Columns present = {}".format(df.columns))
        return None
    # if we have fullname then we are good to go.
    if "studentName" in df.columns:
        print('"studentName" column present')
        df["studentName"].apply(lambda X: X.strip())
        return df

    # we need one of some approx of last-name field
    name0list = ["surname", "familyName", "lastName"]
    name0 = None
    for X in df.columns:
        if X.casefold() in (n.casefold() for n in name0list):
            print('"{}" column present'.format(X))
            name0 = X
            break
    if name0 is None:
        print('Cannot find column to use for "surname", tried {}'.format(name0list))
        print("Columns present = {}".format(df.columns))
        return None
    # strip the excess whitespace
    df[name0] = df[name0].apply(lambda X: X.strip())

    # we need one of some approx of given-name field
    name1list = [
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
    name1 = None
    for X in df.columns:
        if X.casefold() in (n.casefold() for n in name1list):
            print('"{}" column present'.format(X))
            name1 = X
            break
    if name1 is None:
        print('Cannot find column to use for "given name", tried {}'.format(name1list))
        print("Columns present = {}".format(df.columns))
        return None
    # strip the excess whitespace
    df[name1] = df[name1].apply(lambda X: X.strip())

    # concat name0 and name1 fields into fullName field
    # strip excess whitespace from those fields
    df["studentName"] = df[name0] + ", " + df[name1]

    return df


def checkLatinNames(df):
    """Pass the pandas object and check studentNames encode to Latin-1.

    Print out a warning message for any that are not.
    """
    # TODO - make this less eurocentric in the future.
    problems = []
    for index, row in df.iterrows():
        try:
            tmp = row["studentName"].encode("Latin-1")
        except UnicodeEncodeError:
            problems.append(
                'row {}, number {}, name: "{}"'.format(
                    index, row["id"], row["studentName"]
                )
            )
    if len(problems) > 0:
        print("WARNING: The following ID/name pairs contain non-Latin characters:")
        for X in problems:
            print(X)
        return False
    else:
        return True


def acceptedFormats():
    return """The classlist can be a .csv file with column headers:
  • "id" - student ID number
  • "studentName" - student name in a single field

Or the student name can be split into two fields:
  • id
  • surname, familyName, or lastName
  • name, firstName, givenName, nickName, or preferredName

Alternatively, give a .csv exported from Canvas (experimental!)
"""


def processClassList(fname, outputfile):
    """Get student names/numbers from csv, process, and save for server.

    Student numbers come from an `id` column.  There is some
    flexibility about student names: most straightforward is a
    column named `studentNames`.  Otherwise, various columns such as
    `surname` and `name` are tried.

    Alternatively, a csv file exported from Canvas can be provided.

    The results are written into a new csv file in a simplied format.
    """

    with open(fname) as csvfile:
        reader = csv.DictReader(csvfile, skipinitialspace=True)
        fields = reader.fieldnames
    print("Class list headers = {}".format(fields))

    # First check if this is Canvas output
    if all(x in fields for x in ("Student", "ID", "SIS User ID", "SIS Login ID")):
        print("This looks like it was exported from Canvas")
        df = import_canvas_csv(fname)
        print("Extracting columns from Canvas data and renaming")
        df = df[["Student Number", "Student"]]
        df.columns = ["id", "studentName"]
    else:  # Is not canvas so check we have required headers
        df = checkNonCanvasCSV(fname)
        if df is None:
            print("Problems with the classlist you supplied. See output above.")
            exit(1)
        df = df[["id", "studentName"]]

    # check characters in names are latin-1 compatible
    if not checkLatinNames(df):
        print(">>> WARNING <<<")
        print(
            "Potential classlist problems",
            "The classlist you supplied contains non-Latin characters - see console output above. "
            "You can proceed, but it might cause problems later. "
            "Apologies for the eurocentricity.",
        )

    print("Saving to {}".format(outputfile))
    df.to_csv(outputfile, index=False)
