# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020 Colin B. Macdonald

"""
Use sklearn random forest model to read student IDs from ID-pages.
Relies on use of standard ID template.

Note: has hardcoded 8-digit student numbers.

Note: Code in this file is very similar to idReader code for the Tensorflow
model.
"""

import os
from pathlib import Path
import csv

import requests
from lapsolver import solve_dense
import numpy as np

from plom import specdir
from .predictStudentID import compute_probabilities
from .trainRandomForestModel import train_model


def is_model_absent():
    """Checks if the ML model is available.

    Returns:
        boolean: True/False, indicating if the model is present.
    """

    base_path = Path("model_cache")
    files = ["RF_ML_model.sav.gz"]

    for filename in files:
        if not os.path.isfile(base_path / filename):
            return True
    return False


def download_model():
    """Try to download the model, respond with False if unsuccessful.

    Returns:
        boolean: True/False about if the model was successful.
    """
    base_path = Path("model_cache")
    base_url = "https://gitlab.com/plom/plomidreaderdata/-/raw/master/plomBuzzword/"
    files = [
        "RF_ML_model.sav.gz",
    ]
    for file_name in files:
        url = base_url + file_name
        print("Getting {} - ".format(file_name))
        response = requests.get(url)
        if response.status_code != 200:
            print("\tError getting file {}.".format(file_name))
            return False
        with open(base_path / file_name, "wb+") as file_header:
            file_header.write(response.content)
        print("\tDone Saving")
    return True


def download_or_train_model():
    """Dowload the ID detection model if possible, if not, train it."""

    # make a directory into which to save things
    base_path = Path("model_cache")
    # make both the basepath and its variables subdir
    os.makedirs(base_path, exist_ok=True)

    print(
        "Will try to download model and if that fails, then train it locally (which is time-consuming)"
    )
    if download_model():
        print("Successfully downloaded sklearn (Random-Forest) model. Good to go.")
    else:
        print("Could not download the model, need to train model instead.")
        print(
            "This will take some time -- on the order of 2-3 minutes depending on your computer."
        )
        train_model()


def calc_log_likelihood(student_ID, prediction_probs, num_digits):
    """Calculate the log likelihood that an ID prediction matches the student ID.

    Args:
        student_ID (str): Student ID as a string.
        prediction_probs (list): A list of the probabilities predicted by the model.
        num_digits (int): Number of digits in the student ID.

    Returns:
       numpy.float64: log likelihood.
    """

    # pass in the student ID-digits and the prediction_probs
    # prediction_probs = scans[fn]
    # prediction_probs[k][n] = approx prob that digit k of ID is n.
    log_likelihood = 0
    # log_likelihood will be the approx -log(prob) - so more probable means smaller logP.
    # make it negative since we'll minimise "cost" when we do the linear assignment problem stuff below.
    for digit_index in range(0, num_digits):
        digit_predicted = int(student_ID[digit_index])
        log_likelihood -= np.log(
            max(prediction_probs[digit_index][digit_predicted], 1e-30)
        )  # avoids taking log of 0.

    return log_likelihood


def run_id_reader(files_dict, rectangle):
    """Run ID detection on papers and save the prediction results to a csv file.

    Args:
        files_dict (dict): A dictionary of the original paper front page images to
            run the detector on. Of the form {`paper_number`,`paper_image_path`}.
        rectangle (list): A list of the rectangle information of the form
            [top_left_x_coord, top_left_y_coord, x_width, y_height] for the
            cropped rectangle.
    """

    # Number of digits in the student ID.
    num_digits = 8

    # convert rectangle to "top" and "bottom"
    # IDrectangle is a 4-tuple top_left_x, top_left_y, width, height - floats, but we'll need ints.
    top_coordinate = int(rectangle[1])
    bottom_coordinate = int(rectangle[1] + rectangle[3])

    # keeps a list of testNumbers... the ith test in list has testNumber k (i != k?)
    # will need this for cost-matrix
    test_numbers = list(files_dict.keys())

    # check to see if model already there and if not get it or train it.
    if is_model_absent():
        download_or_train_model()
    # probabilities that digit k of ID is "n" for each file.
    # this is potentially time-consuming - could be parallelized
    # pass in the list of files to check, top /bottom of image-region to check.
    print("Computing probabilities")
    probabilities = compute_probabilities(
        files_dict, top_coordinate, bottom_coordinate, num_digits
    )

    # Put student numbers in list
    student_IDs = []
    with open(
        Path(specdir) / "classlist.csv", newline=""
    ) as csvfile:  # todo update file paths
        csv_reader = csv.reader(csvfile, delimiter=",")
        next(csv_reader, None)  # skip the header
        for row in csv_reader:
            student_IDs.append(row[0])

    # now build "costs" -- annoyance is that test-number might not be row number in cost matrix.
    print("Computing cost matrix")
    costs = []
    for test in test_numbers:
        row = []
        for student_ID in student_IDs:
            row.append(calc_log_likelihood(student_ID, probabilities[test], num_digits))
        costs.append(row)

    # use Hungarian method (or similar) https://en.wikipedia.org/wiki/Hungarian_algorithm
    # as coded up in lapsolver
    # to find least cost assignment of tests to studentIDs
    # this is potentially time-consuming, cannot be parallelized.
    print("Going hungarian")
    row_IDs, column_IDs = solve_dense(costs)

    # now save the result
    with open(Path(specdir) / "predictionlist.csv", "w") as file_header:
        file_header.write("test, id\n")
        for r, c in zip(row_IDs, column_IDs):
            # the get test-number of r-th from the test_numbers
            test_number = test_numbers[r]
            # print("{}, {}".format(test_number, student_IDs[c]))
            file_header.write("{}, {}\n".format(test_number, student_IDs[c]))
        file_header.close()

    print("Results saved in predictionlist.csv")
    return
