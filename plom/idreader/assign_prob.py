# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2022-2023 Natalie Balashov

"""
Tools for building and solving assignment problems.
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


def assemble_cost_matrix(test_numbers, student_IDs, probabilities):
    """Compute the cost matrix between list of tests and list of student IDs.

    Args:
        test_numbers (list): int, the ones we want to match.
        probabilities (dict): keyed by testnum (int), to list of lists of floats.
        student_IDs (list): A list of student ID numbers

    Returns:
        list: list of lists of floats representing a matrix.

    Raises:
        KeyError: If probabilities is missing data for one of the test numbers.
    """
    # could precompute big cost matrix, then select rows/columns: more complex
    costs = []
    for test in test_numbers:
        row = []
        for student_ID in student_IDs:
            row.append(calc_log_likelihood(student_ID, probabilities[test]))
        costs.append(row)
    return costs


def lap_solver(test_numbers, student_IDs, probabilities):
    """Run linear assignment problem solver, return prediction results.

    Args:
        test_numbers (list): int, the ones we want to match.
        student_IDs (list): A list of student ID numbers.
        probabilities (dict): dict with keys that contain a test number and values that contain a probability matrix,
        which is a list of lists of floats.

    Returns:
        list: triples of (`paper_number`, `student_ID`, `certainty`),
        where certainty is the mean of digit probabilities for the student_ID selected by LAP solver.

    use Hungarian method (or similar) https://en.wikipedia.org/wiki/Hungarian_algorithm
    (as implemented in the ``lapsolver`` package)
    to find least cost assignment of tests to studentIDs.

    This is potentially time-consuming but in practice for 1000 papers I observed
    a tiny fraction of a section.  The package ``lapsolver`` itself notes
    3000x3000 in around 3 seconds.
    """
    cost_matrix = assemble_cost_matrix(test_numbers, student_IDs, probabilities)

    row_IDs, column_IDs = solve_dense(cost_matrix)

    predictions = []
    for r, c in zip(row_IDs, column_IDs):
        test_num = test_numbers[r]
        sid = student_IDs[c]

        sum_digit_probs = 0
        for digit in range(len(sid)):
            sum_digit_probs += probabilities[test_num][digit][int(sid[digit])]
        certainty = sum_digit_probs / len(sid)

        predictions.append((test_num, sid, certainty))
    return predictions


def greedy(student_IDs, probabilities):
    """Generate greedy predictions for student ID numbers.

    Args:
        student_IDs: integer list of student ID numbers

        probabilities: dict with paper_number -> probability matrix.
        Each matrix contains probabilities that the ith ID char is matched with digit j.

    Returns:
        list: a list of tuples (paper_number, id_prediction, certainty)

    Algorithm:
        For each entry in probabilities, check each student id in the classlist against the matrix.
        The probabilities corresponding to the digits in the student id are extracted.
        Calculate a mean of those digit probabilities, and choose the student id that yielded the highest mean value.
        The calculated digit probabilities mean is returned as the "certainty".
    """
    predictions = []

    for paper_num in probabilities:
        sid_probs = []

        for id_num in student_IDs:
            sid = str(id_num)
            digit_probs = []

            for i in range(len(sid)):
                # find the probability of digit i in sid
                i_prob = probabilities[paper_num][i][int(sid[i])]
                digit_probs.append(i_prob)

            # calculate the mean of all digit probabilities
            mean = sum(digit_probs) / len(sid)
            sid_probs.append(mean)

        # choose the sid with the highest mean digit probability
        largest_prob = sid_probs.index(max(sid_probs))
        predictions.append((paper_num, student_IDs[largest_prob], max(sid_probs)))

    return predictions
