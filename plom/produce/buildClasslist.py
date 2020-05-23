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
from pathlib import Path

import pkg_resources
import pandas

from ..finish.return_tools import import_canvas_csv
from plom import specdir



possible_lastname_list = ["surname", "familyName", "lastName"]

possible_firstname_list = [
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
    """ Read the csv file and clean the csv file
        1- Retreive the id
        2- Retreive the studentName is preset
        3- If not, retreive student given name and surname in the document
        
        IMPORTANT: This function must be run after being checked
        by check_is_non_canvas_csv, otherwise this would not work

    Arguments:
        csv_file_name {Str} -- Name of the csv file

    Returns:
        pandas.core.frame.DataFrame -- Dataframe object returned with columns id and studentName
    """

    student_info_data_frame = pandas.read_csv(csv_file_name, dtype="object")
    print('Loading from non-Canvas csv file to clean the column titles: "{0}"'.format(csv_file_name))

    # strip excess whitespace from column names
    student_info_data_frame.rename(columns=lambda x: x.strip(), inplace=True)

    # now check we have the columns needed
    if "id" in student_info_data_frame.columns:
        print('"id" column present')
        # strip excess whitespace
        student_info_data_frame["id"] = student_info_data_frame["id"].apply(lambda X: X.strip())
    
    # if we have fullname then we are good to go.
    if "studentName" in student_info_data_frame.columns:
        print('"studentName" column present')
        student_info_data_frame["studentName"].apply(lambda X: X.strip())
        return student_info_data_frame

    # Otherwise, we will check the titles again
    # we need one of some approx of last-name field
    firstname_column_title = None
    for column_title in student_info_data_frame.columns:
        if column_title.casefold() in (possible_title.casefold() for possible_title in possible_lastname_list):
            print('"{}" column present'.format(column_title))
            firstname_column_title = column_title
            break
    # strip the excess whitespace
    student_info_data_frame[firstname_column_title] = student_info_data_frame[firstname_column_title].apply(lambda X: X.strip())


    # we need one of some approx of given-name field
    lastname_column_title = None
    for column_title in student_info_data_frame.columns:
        if column_title.casefold() in (possible_title.casefold() for possible_title in possible_firstname_list):
            print('"{}" column present'.format(column_title))
            lastname_column_title = column_title
            break
    # strip the excess whitespace
    student_info_data_frame[lastname_column_title] = student_info_data_frame[lastname_column_title].apply(lambda X: X.strip())

    # concat firstname_column_title and lastname_column_title fields into fullName field
    # strip excess whitespace from those fields
    student_info_data_frame["studentName"] = student_info_data_frame[firstname_column_title] + ", " + student_info_data_frame[lastname_column_title]

    student_info_data_frame.columns = ["id", "studentName"]

    return student_info_data_frame




def check_is_non_canvas_csv(csv_file_name):
    """ Read the csv file and check to see if the id and student name exist.
        1- Check if id is present
        2- Check if studentName is preset
        3- If not, check for given name and surname in the document
        
        IMPORTANT: This function must be run before clean_non_canvas_csv

    Arguments:
        csv_file_name {Str} -- Name of the csv file

    Returns:
        bool -- True/False
    """

    student_info_data_frame = pandas.read_csv(csv_file_name, dtype="object")
    print('Loading from non-Canvas csv file to check file: "{0}"'.format(csv_file_name))
    
    # strip excess whitespace from column names
    student_info_data_frame.rename(columns=lambda x: x.strip(), inplace=True)

    if "id" not in student_info_data_frame.columns:
        print('Cannot find "id" column')
        print("Columns present = {}".format(student_info_data_frame.columns))
        return False
    
    # if we have don't have  then we are good to go.
    if "studentName" not in student_info_data_frame.columns:
        
        # we need one of some approx of last-name field
        firstname_column_title = None
        for column_title in student_info_data_frame.columns:
            if column_title.casefold() in (possible_title.casefold() for possible_title in possible_lastname_list):
                print('"{}" column present'.format(column_title))
                firstname_column_title = column_title
                break
        if firstname_column_title is None:
            print('Cannot find column to use for "surname", tried {}'.format(possible_lastname_list))
            print("Columns present = {}".format(student_info_data_frame.columns))
            return False
        
        # we need one of some approx of given-name field
        lastname_column_title = None
        for column_title in student_info_data_frame.columns:
            if column_title.casefold() in (possible_title.casefold() for possible_title in possible_firstname_list):
                print('"{}" column present'.format(column_title))
                lastname_column_title = column_title
                break
        if lastname_column_title is None:
            print('Cannot find column to use for "given name", tried {}'.format(possible_firstname_list))
            print("Columns present = {}".format(student_info_data_frame.columns))
            return False
    
    return True
    



def clean_canvas_csv(csv_file_name):
    """ Read the canvas csv file and clean the csv file
        
        IMPORTANT: This function must be run after being checked
        by check_is_canvas_csv, otherwise this would not work

    Arguments:
        csv_file_name {Str} -- Name of the csv file

    Returns:
        pandas.core.frame.DataFrame -- Dataframe object returned with columns id and studentName
    """
    student_info_data_frame = import_canvas_csv(csv_file_name)
    student_info_data_frame = student_info_data_frame[["Student Number", "Student"]]
    student_info_data_frame.columns = ["id", "studentName"]
    return student_info_data_frame



def check_is_canvas_csv(csv_file_name):
    """ Checks to see if a function is a canvas style csv file
        
        IMPORTANT: This function must be run before clean_canvas_csv

    Arguments:
        csv_file_name {Str} -- Name of the csv file

    Returns:
        boolean -- True/False
    """
    with open(csv_file_name) as csvfile:
        csv_reader = csv.DictReader(csvfile, skipinitialspace=True)
        csv_fields = csv_reader.fieldnames
    return all(x in csv_fields for x in canvas_columns_format)




def check_latin_names(student_info_data_frame):
    """ Pass the pandas object and check studentNames encode to Latin-1
        Print out a warning message for any that are not
        Note: This functions prints warnings about the encoding issues

    Arguments:
        student_info_data_frame {pandas.core.frame.DataFrame} -- Dataframe object returned with columns id and studentName

    Returns:
        bool -- True/False
    """

    # TODO - make this less eurocentric in the future.
    encoding_problems = []
    for index, row in student_info_data_frame.iterrows():
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



def process_classlist_backend(student_csv_file_name, outputfile):
    """ Processes the classlist depending on weter its a canvas style csv folder or if it isn't 
        1- Check if the file is canvas style csv, if so clean 
        2- Otherwise check if te function has the id/name info, if so clean it 
        3- Otherwise exit(1)
        4- If not exited, check for latin character encodability

    Arguments:
        student_csv_file_name {Str} -- Name of the class info csv file
        outputfile {pathlib.PosixPath} -- Output file for the saved csv file
    """

    with open(student_csv_file_name) as csvfile:
        csv_reader = csv.DictReader(csvfile, skipinitialspace=True)
        csv_fields = csv_reader.fieldnames
    print("Class list headers = {}".format(csv_fields))

    # Depending on the type of file, wether its a Canvas file or not, 
    # we need to check it has the minimum information ie student name/id.
    # If not we will fail the process.
    
    # First we check if this csv file is a Canvas output using check_canvas_csv
    if check_is_canvas_csv(student_csv_file_name):
        print("This file looks like it was exported from Canvas")
        student_info_data_frame = clean_canvas_csv(student_csv_file_name)
        print("We have successfully extracted columns from Canvas data and renaming")
    # Is not a Canvas formed file, we will check if the canvas data is usable using check_non_canvas_csv
    elif check_is_non_canvas_csv(student_csv_file_name):
        print("This file looks like it was not exported from Canvas, we will check the function for the required information")
        student_info_data_frame = clean_non_canvas_csv(student_csv_file_name)           
        print("We have successfully extracted and renamed columns from the non Canvas data and have the required information")
    # Otherwise we have an error
    else:
        print("Problems with the classlist you supplied. See output above.")
        exit(1)

    # Check characters in names are latin-1 compatible
    if not check_latin_names(student_info_data_frame):
        print(">>> WARNING <<<")
        print(
            "Potential classlist problems",
            "The classlist you supplied contains non-Latin characters - see console output above. "
            "You can proceed, but it might cause problems later. "
            "Apologies for the eurocentricity.",
        )

    print("Saving to {}".format(outputfile))
    student_info_data_frame.to_csv(outputfile, index=False)




def process_class_list(student_csv_file_name, demo=False):
    """ Get student names/numbers from csv, process, and save for server
        
        Student numbers come from an `id` column.  There is some
        flexibility about student names: most straightforward is a
        second column named `studentNames`.  The results are copied
        into a new csv file in a simplied format.
        
        The classlist can be a .csv file with column headers:
        • `id` - student ID number
        • `studentName` - student name in a single field

        Or the student name can be split into two fields:
        • id
        • surname, familyName, or lastName
        • name, firstName, givenName, nickName, or preferredName

        Alternatively, give a .csv exported from Canvas (experimental!)

    Arguments:
        student_csv_file_name {Str} -- Name of the class info csv file

    Keyword Arguments:
        demo {bool} -- Indicating whether we are in demo mode (default: {False})
    """

    os.makedirs(specdir, exist_ok=True)
    if os.path.isfile(Path(specdir) / "classlist.csv"):
        print(
            "Classlist file already present in '{}' directory. Aborting.".format(specdir)
        )
        exit(1)
        pass

    if demo:
        print("Using demo classlist - DO NOT DO THIS FOR A REAL TEST")
        cl = pkg_resources.resource_string("plom", "demoClassList.csv")
        with open(Path(specdir) / "classlist.csv", "wb") as fh:
            fh.write(cl)
        return

    if not student_csv_file_name:
        print("Please provide a classlist file: see help")
        exit(1)

    # grab the file, process it and copy it into place.
    if os.path.isfile(student_csv_file_name):
        process_classlist_backend(student_csv_file_name, Path(specdir) / "classlist.csv")
    else:
        print('Cannot find file "{}"'.format(student_csv_file_name))
        exit(1)
