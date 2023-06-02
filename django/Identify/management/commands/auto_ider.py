# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (c) 2022 Edith Coates
# Copyright (C) 2022-2023 Natalie Balashov


import math
from pathlib import Path

import numpy as np
import cv2
import imutils
from imutils.perspective import four_point_transform

from .model_utils import load_model


from lapsolver import solve_dense
import numpy as np

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Management command for ID reading and matching.

    python3 manage.py auto_ider
    """

    help = ""

    def func_name(self, top, bottom, left, right):
        idservice = IDReaderService()
        box = (top, bottom, left, right)
        if any(x is None for x in box):
            if all(x is None for x in box):
                box = None
            else:
                raise CommandError("If you provide one dimension you must provide all")
        try:
            idservice.get_id_box_cmd(box)
            self.stdout.write("Extracted the ID box from all known ID pages.")
        except ValueError as err:
            raise CommandError(err)

##########################################################################################
########################## SERVER FUNCTIONS ##############################################

def get_sids_and_probabilities():
    """Retrieve student ID numbers from `classlist.csv` and
       probability data from `id_prob_heatmaps.json`

    Returns:
        tuple: a 2-tuple consisting of two lists, where the first contains student ID numbers
               and the second contains the probability data

    Raises:
        RuntimeError: id reader still running
        FileNotFoundError: no probability data
    """
    heatmaps_file = specdir / "id_prob_heatmaps.json"

    # implicitly raises FileNotFoundError if no heatmap
    with open(heatmaps_file, "r") as fh:
        probabilities = json.load(fh)
    # ugh, undo Json mucking our int keys into str
    probabilities = {int(k): v for k, v in probabilities.items()}

    log.info("Getting the classlist")
    sids = []
    with open(specdir / "classlist.csv", newline="") as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=",")
        next(csv_reader, None)  # skip the header
        for row in csv_reader:
            sids.append(row[0])

    return sids, probabilities


def predict_id_greedy(self):
    """Match each unidentified paper against best fit in classlist.

    Insert these predictions into the database as "MLGreedy" predictions.

    Returns:
        string: a message that communicates whether the predictions were
        successfully inserted into the DB.
    """
    sids, probabilities = get_sids_and_probabilities()
    greedy_predictions = greedy(sids, probabilities)

    # temporary, for debugging/experimenting
    # with open(specdir / "greedy_predictions.json", "w") as f:
    #     json.dump(greedy_predictions, f)

    ok, msg = self.ID_put_predictions(greedy_predictions, "MLGreedy")
    assert ok
    return msg


def predict_id_lap_solver(self):
    """Matching unidentified papers against classlist via linear assignment problem.

    Get the classlist and remove all people that are already IDed
    against a paper.  Get the list of unidentified papers.

    Probably some cannot be read: drop those from the list of unidentified
    papers.

    Match the two.

    Insert these predictions into the database as "MLLAP" predictions.

    TODO: consider doing this client-side, although Manager tool would
    then depend on lapsolver or perhaps SciPy's linear_sum_assignment

    Returns:
        str: multiline status text, appropriate to show to a user.

    Raises:
        IndexError: something is zero, degenerate assignment problem.
    """
    sids, probabilities = get_sids_and_probabilities()

    status = f"Original class list has {len(sids)} students.\n"

    X = self.DB.IDgetIdentifiedTests()
    for x in X:
        try:
            sids.remove(x[1])
        except ValueError:
            pass

    unidentified_papers = self.DB.IDgetUnidentifiedTests()
    status += "\nAssignment problem: "
    status += f"{len(unidentified_papers)} unidentified papers to match with "
    status += f"{len(sids)} unused names in the classlist."

    # exclude papers for which we don't have probabilities
    papers = [n for n in unidentified_papers if n in probabilities]
    if len(papers) < len(unidentified_papers):
        status += f"\nNote: {len(unidentified_papers) - len(papers)} papers "
        status += f"were not autoread; have {len(papers)} papers to match.\n"

    if len(papers) == 0 or len(sids) == 0:
        raise IndexError(
            f"Assignment problem is degenerate: {len(papers)} unidentified "
            f"machine-read papers and {len(sids)} unused students."
        )

    status += "\nBuilding cost matrix and solving assignment problem..."
    t = time.process_time()
    lap_predictions = lap_solver(papers, sids, probabilities)
    status += f" done in {time.process_time() - t:.02} seconds."

    # temporary, for debugging/experimenting
    # with open(specdir / "lap_predictions.json", "w") as f:
    #     json.dump(lap_predictions, f)

    ok, msg = self.ID_put_predictions(lap_predictions, "MLLAP")
    assert ok
    status += "\n" + msg

    return status

##########################################################################################
########################### MATCHING FUNCTIONS #########################################

    def calc_log_likelihood(self, student_ID, prediction_probs):
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


    def assemble_cost_matrix(self, test_numbers, student_IDs, probabilities):
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


    def lap_solver(self, test_numbers, student_IDs, probabilities):
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


    def greedy(self, student_IDs, probabilities):
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
#########################################################################################
##########################################################################################


    def add_arguments(self, parser):
        parser.add_argument(
            "top",
            type=float,
            help="top bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        parser.add_argument(
            "bottom",
            type=float,
            help="bottom bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        parser.add_argument(
            "left",
            type=float,
            help="left bound of rectangle to extract",
            default=None,
            nargs="?",
        )
        parser.add_argument(
            "right",
            type=float,
            help="right bound of rectangle to extract",
            default=None,
            nargs="?",
        )

    def handle(self, *args, **options):
        self.get_id_box(
            options["top"], options["bottom"], options["left"], options["right"]
        )
