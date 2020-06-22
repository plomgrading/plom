# -*- coding: utf-8 -*-

"""
Use tensorflow model to read student IDs from ID-pages.
Relies on use of standard ID template.
"""

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

import os
from pathlib import Path
import csv

import requests
from lapsolver import solve_dense
import numpy as np

from plom import specdir
from .predictStudentID import compute_probabilities


def is_model_absent():
    """Checks if we have the files for the model downloaded.

    Returns:
        bool -- True if model files are present, False otherwise.
    """
    # this directory is created with downloadModel is called
    basePath = Path("plomBuzzword")
    files = [
        "saved_model.pb",
        "variables/variables.index",
        "variables/variables.data-00000-of-00001",
    ]
    for fn in files:
        if os.path.isfile(basePath / fn):
            continue
        else:
            return True
    return False


def download_model():
    """Downloads the model from the gitlab repository.

    Returns:
        bool -- True if successful, False otherwise.
    """
    # make a directory into which to save things
    basePath = Path("plomBuzzword")
    # make both the basepath and its variables subdir
    os.makedirs(basePath / "variables", exist_ok=True)

    baseUrl = "https://gitlab.com/plom/plomidreaderdata/-/raw/master/plomBuzzword/"
    files = [
        "saved_model.pb",
        "variables/variables.index",
        "variables/variables.data-00000-of-00001",
    ]
    for fn in files:
        url = baseUrl + fn
        print("Getting {} - ".format(fn))
        response = requests.get(url)
        if response.status_code != 200:
            print("\tError getting file {}.".format(fn))
            return False
        else:
            print("\tDone.")
        with open(basePath / fn, "wb+") as fh:
            fh.write(response.content)
    return True


def download_or_train_model():
    """Gives us a local, working model either through downloading a model or training the Tensorflow model from scratch."""
    print(
        "Will try to download model and if that fails, then build it locally (which is time-consuming)"
    )
    if download_model():
        print("Successfully downloaded tensorflow model.")
    else:
        print("Could not download the model, need to train model instead.")
        print(
            "This will take some time -- on the order of 10-20 minutes depending on your computer."
        )
        from .IDReader.trainModelTensorFlow import train_and_save_model

        train_and_save_model()


def log_likelihood(student_ids, probabilities):
    """Calculates the (negative) log likelihood for digits detected.

    Arguments:
        student_ids {list} -- list of the correct student numbers we are looking for.
        probabilities {list} -- probabilities[k][n] = approx probability that digit k of ID is n.

    Returns:
        float -- sum of the negative log likelihoods that each digit of student_ids digit is present.
    """
    logP = 0
    # logP will be the approx -log(prob) - so more probable means smaller logP.
    # make it negative since we'll minimise "cost" when we do the linear assignment problem stuff below.
    for k in range(0, 8):
        d = int(student_ids[k])
        logP -= np.log(max(probabilities[k][d], 1e-30))  # avoids taking log of 0.
    return logP


def run_id_reader(file_dict, rectangle):
    """Reads the ids for given test numbers in a directory (and test page configuration).

    Arguments:
        file_dict {dict} -- test number -> filename.
        rectangle {list} -- contains the four corners of the rectangle the id (should) exist in.
    """
    # convert rectangle to "top" and "bottom"
    # rectangle is a 4-tuple left,top,width,height - floats, but we'll need ints.
    top = int(rectangle[1])
    bottom = int(rectangle[1] + rectangle[3])

    # keeps a list of testNumbers... the ith test in list has testNumber k (i != k?)
    # will need this for cost-matrix
    testList = list(file_dict.keys())

    # check to see if model already there and if not get it or train it.
    if is_model_absent():
        download_or_train_model()
    # probabilities that digit k of ID is "n" for each file.
    # this is potentially time-consuming - could be parallelized
    # pass in the list of files to check, top /bottom of image-region to check.
    print("Computing probabilities")
    probabilities = compute_probabilities(file_dict, top, bottom)
    # put studentNumbers in list
    studentNumbers = []
    with open(Path(specdir) / "classlist.csv", newline="") as csvfile:
        red = csv.reader(csvfile, delimiter=",")
        next(red, None)  # skip the header
        for row in red:
            studentNumbers.append(row[0])
    # now build "costs" -- annoyance is that test-number might not be row number in cost matrix.
    print("Computing cost matrix")
    costs = []
    for test in testList:
        lst = []
        for sid in studentNumbers:
            lst.append(log_likelihood(sid, probabilities[test]))
        costs.append(lst)
    # use Hungarian method (or similar) https://en.wikipedia.org/wiki/Hungarian_algorithm
    # as coded up in lapsolver
    # to find least cost assignment of tests to studentIDs
    # this is potentially time-consuming, cannot be parallelized.
    print("Going hungarian")
    rowIDs, columnIDs = solve_dense(costs)

    # now save the result
    with open(Path(specdir) / "predictionlist.csv", "w") as fh:
        fh.write("test, id\n")
        for r, c in zip(rowIDs, columnIDs):
            # the get test-number of r-th from the testList
            testNumber = testList[r]
            # print("{}, {}".format(testNumber, studentNumbers[c]))
            fh.write("{}, {}\n".format(testNumber, studentNumbers[c]))
        fh.close()
    print("Results saved in predictionlist.csv")
