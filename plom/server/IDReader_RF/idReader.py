# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2022 Colin B. Macdonald

"""
Use sklearn random forest model to read student IDs from ID-pages.
Relies on use of standard ID template.

Note: has hardcoded 8-digit student numbers.
"""

from lapsolver import solve_dense
import numpy as np

from .model_utils import download_or_train_model
from .predictStudentID import compute_probabilities


def calc_log_likelihood(student_ID, prediction_probs):
    """Calculate the log likelihood that an ID prediction matches the student ID.

    Args:
        student_ID (str): Student ID as a string.
        prediction_probs (list): A list of the probabilities predicted
            by the model.
            `prediction_probs[k][n]` is the probability that digit k of
            ID is n.

    Returns:
        numpy.float64: log likelihood.  Approx -log(prob), so more
            probable means smaller.  Negative since we'll minimise
            "cost" when we do the linear assignment problem later.
    """
    num_digits = len(student_ID)
    if len(prediction_probs) != num_digits:
        raise ValueError("Wrong length")

    log_likelihood = 0
    for digit_index in range(0, num_digits):
        digit_predicted = int(student_ID[digit_index])
        log_likelihood -= np.log(
            max(prediction_probs[digit_index][digit_predicted], 1e-30)
        )  # avoids taking log of 0.

    return log_likelihood


def run_id_reader(files_dict, rectangle, student_IDs):
    """Run ID detection on papers and save the prediction results to a csv file.

    Args:
        files_dict (dict): A dictionary of the original paper front page images to
            run the detector on. Of the form {`paper_number`,`paper_image_path`}.
        rectangle (list): A list of the rectangle information of the form
            [top_left_x_coord, top_left_y_coord, x_width, y_height] for the
            cropped rectangle.
        student_IDs (list): A list of student ID numbers

    Returns:
        list: pairs of (`paper_number`, `student_ID`).
    """
    # Number of digits in the student ID.
    student_number_length = 8

    # convert rectangle to "top" and "bottom"
    # IDrectangle is a 4-tuple top_left_x, top_left_y, width, height - floats, but we'll need ints.
    top_coordinate = int(rectangle[1])
    bottom_coordinate = int(rectangle[1] + rectangle[3])

    # keeps a list of testNumbers... the ith test in list has testNumber k (i != k?)
    # will need this for cost-matrix
    test_numbers = list(files_dict.keys())
    # we may skip some tests if hard to extract the ID boxes
    test_numbers_used = []

    download_or_train_model()

    # probabilities that digit k of ID is "n" for each file.
    # this is potentially time-consuming - could be parallelized
    # pass in the list of files to check, top /bottom of image-region to check.
    print("Computing probabilities")
    probabilities = compute_probabilities(
        files_dict, top_coordinate, bottom_coordinate, student_number_length
    )

    # now build "costs" -- annoyance is that test-number might not be row number in cost matrix.
    print("Computing cost matrix")
    costs = []
    for test in test_numbers:
        if test not in probabilities:
            print(f"Test {test} is excluded")
            continue
        test_numbers_used.append(test)
        row = []
        for student_ID in student_IDs:
            row.append(calc_log_likelihood(student_ID, probabilities[test]))
        costs.append(row)

    # use Hungarian method (or similar) https://en.wikipedia.org/wiki/Hungarian_algorithm
    # as coded up in lapsolver
    # to find least cost assignment of tests to studentIDs
    # this is potentially time-consuming, cannot be parallelized.
    print("Going hungarian")
    row_IDs, column_IDs = solve_dense(costs)

    prediction_pairs = []

    for r, c in zip(row_IDs, column_IDs):
        # the get test-number of r-th from the test_numbers_used
        # since we may have skipped a few tests with hard-to-read IDs
        test_number = test_numbers_used[r]
        prediction_pairs.append((test_number, student_IDs[c]))

    return prediction_pairs
