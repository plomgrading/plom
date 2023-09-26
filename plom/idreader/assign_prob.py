# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2022-2023 Natalie Balashov

"""Tools for building and solving assignment problems."""

from typing import List

import numpy as np


def calc_log_likelihood(
    student_ID: str, prediction_probs: List[List[float]]
) -> np.float64:
    """Calculate the log likelihood that an ID prediction matches the student ID.

    Args:
        student_ID: Student ID as a string of digit characters.
        prediction_probs: A list of lists of the probabilities
            predicted by the model, where
            ``prediction_probs[k][n]`` is the probability that
            digit ``k`` of ID is ``n``.

    Returns:
        log likelihood, approx -log(prob), so more probable means smaller.
        Negative since we'll minimise
        "cost" when we do the linear assignment problem later.

    Raises:
        ValueError: unexpected mismatches such as short student ID.
            or non-integer characters in the student ID.
            For example, if the student ID contains a "z", we'd get
            ``invalid literal for int() with base 10: z``.
    """
    num_digits = len(student_ID)
    if len(prediction_probs) != num_digits:
        raise ValueError(
            f'Length mismatch: {num_digits} in student ID "{student_ID}"'
            f" but {len(prediction_probs)} probabilities"
        )

    log_likelihood = np.float64(0)
    for digit_index in range(0, num_digits):
        try:
            digit_predicted = int(student_ID[digit_index])
        except ValueError as e:
            raise ValueError(
                f'Student ID digit {digit_index} of "{student_ID}"'
                f" cannot be converted to an integer: {e}"
            ) from e
        log_likelihood -= np.log(
            max(prediction_probs[digit_index][digit_predicted], 1e-30)
        )  # avoids taking log of 0.

    return log_likelihood


def assemble_cost_matrix(
    test_numbers, student_IDs, probabilities
) -> List[List[np.float64]]:
    """Compute the cost matrix between list of tests and list of student IDs.

    Args:
        test_numbers (list): int, the ones we want to match.
        probabilities (dict): keyed by testnum (int), to list of lists of floats.
        student_IDs (list): A list of student ID numbers

    Returns:
        A matrix as a list of lists of floats.

    Raises:
        KeyError: If probabilities is missing data for one of the test numbers.
        ValueError: various unexpected stuff about student IDs, coming
            from the ``calc_log_likelihood`` function.
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

    Use a version of the Jonker-Volgenant algorithm, as cited by SciPy,
    to find least cost assignment of tests to studentIDs.

    This is potentially time-consuming but in practice for 1000 papers I observed
    a tiny fraction of a section.
    """
    from scipy.optimize import linear_sum_assignment

    cost_matrix = assemble_cost_matrix(test_numbers, student_IDs, probabilities)

    row_IDs, column_IDs = linear_sum_assignment(cost_matrix)

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
