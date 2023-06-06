# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2020 Andrew Rechnitzer
# Copyright (C) 2020 Dryden Wiebe
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2022-2023 Natalie Balashov

import csv
import numpy as np
from pathlib import Path
from scipy.optimize import linear_sum_assignment

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from Identify.services import IdentifyTaskService


class Command(BaseCommand):
    """Management command for ID reading and matching.

    python3 manage.py auto_ider
    """

    help = "Run matching tools to generate predictions."

    def run_auto_iding(self):
        try:
            sids, probs = self.get_sids_and_probabilities()
            self.predict_id_greedy(sids, probs)
            self.predict_id_lap_solver(sids, probs)
            self.stdout.write("Ran Greedy and Linear Assignment matching problems and saved results to two CSV files.")
        except ValueError as err:
            raise CommandError(err)

    def get_sids_and_probabilities():
        """Retrieve student ID numbers from `classlist.csv` and
           probability data from `id_prob_heatmaps.json`

        Returns:
            tuple: a 2-tuple consisting of two lists, where the first contains student ID numbers
                   and the second contains the probability data

        Raises:
            FileNotFoundError: no probability data
        """
        heatmaps_file = specdir / "id_prob_heatmaps.json"

        # implicitly raises FileNotFoundError if no heatmap
        with open(heatmaps_file, "r") as fh:
            probabilities = json.load(fh)
        # ugh, undo Json mucking our int keys into str
        probabilities = {int(k): v for k, v in probabilities.items()}

        self.stdout.write("Getting the classlist")
        sids = []
        with open(specdir / "classlist.csv", newline="") as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=",")
            next(csv_reader, None)  # skip the header
            for row in csv_reader:
                sids.append(row[0])

        return sids, probabilities

    def predict_id_greedy(self, sids, probabilities):
        """Match each unidentified paper against best fit in classlist.

        Returns:
            None: instead saves result to a csv file.
        """
        greedy_predictions = greedy(sids, probabilities)

        with open(settings.MEDIA_ROOT / "greedy_predictions.csv", "w") as f:
            write = csv.writer(f)
            write.writerow(("paper_num", "student_ID", "certainty"))
            write.writerows(lap_predictions)

    def predict_id_lap_solver(self, sids, probabilities):
        """Matching unidentified papers against classlist via linear assignment problem.

        Get the classlist and remove all people that are already IDed
        against a paper.  Get the list of unidentified papers.

        Probably some cannot be read: drop those from the list of unidentified
        papers.

        Match the two.

        Returns:
            None: instead saves result to a csv file.

        Raises:
            IndexError: something is zero, degenerate assignment problem.
        """
        self.stdout.write(f"Original class list has {len(sids)} students.\n")

        id_task_service = IdentifyTaskService()
        ided_papers = id_task_service.get_all_identified_tasks()
        for paper in ided_papers:
            try:
                sids.remove(paper[1])
            except ValueError:
                pass

        unidentified_papers = id_task_service.get_unidentified_tasks()
        self.stdout.write("\nAssignment problem: ")
        self.stdout.write(f"{len(unidentified_papers)} unidentified papers to match with " + 
                f"{len(sids)} unused names in the classlist.")

        # exclude papers for which we don't have probabilities
        papers = [n for n in unidentified_papers if n in probabilities]
        if len(papers) < len(unidentified_papers):
            self.stdout.write(f"\nNote: {len(unidentified_papers) - len(papers)} papers " + 
                    f"were not autoread; have {len(papers)} papers to match.\n")

        if len(papers) == 0 or len(sids) == 0:
            raise IndexError(
                f"Assignment problem is degenerate: {len(papers)} unidentified "
                f"machine-read papers and {len(sids)} unused students."
            )

        self.stdout.write("\nBuilding cost matrix and solving assignment problem...")
        t = time.process_time()
        lap_predictions = lap_solver(papers, sids, probabilities)
        self.stdout.write(f" done in {time.process_time() - t:.02} seconds.")

        with open(settings.MEDIA_ROOT / "lap_predictions.csv", "w") as f:
            write = csv.writer(f)
            write.writerow(("paper_num", "student_ID", "certainty"))
            write.writerows(lap_predictions)

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
                row.append(self.calc_log_likelihood(student_ID, probabilities[test]))
            costs.append(row)
        return costs

    def lap_solver(self, test_numbers, student_IDs, probabilities):
        """Run SciPy's linear sum assignment problem solver, return prediction results.

        Args:
            test_numbers (list): int, the ones we want to match.
            student_IDs (list): A list of student ID numbers.
            probabilities (dict): dict with keys that contain a test number and values that contain a probability matrix,
            which is a list of lists of floats.

        Returns:
            list: triples of (`paper_number`, `student_ID`, `certainty`),
            where certainty is the mean of digit probabilities for the student_ID selected by LAP solver.
        """
        cost_matrix = self.assemble_cost_matrix(test_numbers, student_IDs, probabilities)

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
