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


def assemble_cost_matrix(test_numbers, probabilities, student_IDs):
    """Compute the cost matrix between list of tests and list of student IDs.

    TODO: log not print throughout

    Args:
        test_numbers (list): int, the ones we want to match.
        probabilities (dict): keyed by testnum (int), to list of lists of floats.
        student_IDs (list): A list of student ID numbers

    Returns:
        list: list of lists of floats representing a matrix.

    Raises:
        KeyError: TODO?  If probabilities is missing data for one of the test numbers.
    """
    # we may skip some tests if hard to extract the ID boxes
    test_numbers_used = []

    # could precompute big cost matrix, then select rows/columns: more complex
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
    return test_numbers_used, costs


def run_lap_solver(test_numbers, probabilities, student_IDs):
    """Run linear assignment problem solver, return prediction results.

    TODO: log not print throughout

    Args:
        test_numbers (list): int, the ones we want to match.
        probabilities (dict): keyed by testnum (int), to list of lists of floats.
        student_IDs (list): A list of student ID numbers

    Returns:
        list: pairs of (`paper_number`, `student_ID`).
    """
    test_numbers_used, costs = assemble_cost_matrix(test_numbers, probabilities, student_IDs)

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
