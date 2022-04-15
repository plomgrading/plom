# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

import csv
from datetime import datetime
import json
import logging
import os
import shutil
import subprocess
import time

from plom import specdir
from plom.idreader.assign_prob import assemble_cost_matrix, lap_solver


log = logging.getLogger("servID")


def IDprogressCount(self):
    """Send back current ID progress counts to the client.

    Returns:
        list: A list including the number of identified papers
            and the total number of papers.
    """
    return [self.DB.IDcountIdentified(), self.DB.IDcountAll()]


def IDgetNextTask(self):
    """Send the ID number of the next task.

    Returns:
        list: A list including the next task number.
    """
    # Get number of next unidentified test from the database
    give = self.DB.IDgetNextTask()
    if give is None:
        return [False]
    else:
        return [True, give]


def IDgetDoneTasks(self, username):
    """Return the list of already Id's papers by the user.

    Args:
        username (str): Username requesting done tasks.

    Returns:
        list: A list of list with sublists of the form
            [paper_number, user_ID, username]
    """

    return self.DB.IDgetDoneTasks(username)


def IDgetImage(self, username, test_number):
    """Respond with a list of image paths the ID pages of a paper.

    Args:
        username (str): Username requesting ID'd paper's image.
        test_number (str): Test number.

    Returns:
        2-tuple: True/False plus the image paths or a short error code.
    """
    return self.DB.IDgetImage(username, test_number)


def ID_get_donotmark_images(self, paper_number):
    """Respond with a list of image paths for the Do Not Mark pages of a paper.

    Args:
        test_number (str): Test number.

    Returns:
        2-tuple: True/False plus a list of the image paths or a short error code.
    """
    return self.DB.ID_get_donotmark_images(paper_number)


def IDclaimThisTask(self, username, test_number):
    """Assign claimed task in database if possible.

    Args:
        username (str): Username claiming the task.
        test_number (str): Test ID number.

    Returns:
        2-tuple: True/False plus the image paths or a short error code.
    """
    return self.DB.IDgiveTaskToClient(username, test_number)


def pre_id_paper(self, *args, **kwargs):
    """Put a student id into database prediction table, manager only."""
    return self.DB.add_or_change_id_prediction(*args, **kwargs)


def remove_id_prediction(self, *args, **kwargs):
    """Remove a particular test from the database prediction table, manager only."""
    return self.DB.remove_id_prediction(*args, **kwargs)


def ID_id_paper(self, *args, **kwargs):
    """Assign a student name/id combination to a paper in the database."""
    return self.DB.ID_id_paper(*args, **kwargs)


def IDgetImageFromATest(self):
    """Return a random front page exam image for ID box selection by the client.

    Returns:
        list: True/False plus a list of the images' paths.
    """

    return self.DB.IDgetImageFromATest()


def ID_get_predictions(self):
    """Return dict of test:(sid, sname, certainty) of all predictions in DB"""

    return self.DB.ID_get_all_predictions()


def IDdeletePredictions(self):
    """Delete the latest result from ID prediction/detection file.

    Log activity.

    Returns:
        list: first entry is True/False for success.  If False, second
            entry is a string with an explanation.
    """

    # check to see if predictor is running
    lock_file = specdir / "IDReader.lock"
    if os.path.isfile(lock_file):
        log.info("ID reader currently running.")
        return [False, "ID reader is currently running"]

    # move old file out of way
    if not os.path.isfile(specdir / "predictionlist.csv"):
        return [False, "No prediction file present."]
    shutil.move(specdir / "predictionlist.csv", specdir / "predictionlist.bak")
    with open(specdir / "predictionlist.csv", "w") as fh:
        fh.write("test, id\n")
    log.info("ID prediction list deleted")

    return [True]


def IDputPredictions(self, predictions, classlist, spec):
    """Push predictions to the database

    Note - does sanity checks against the current classlist

    Args:
        predictions (list): A list of pairs of (testnumber, student id)
        classlist (list): A list of pairs of (student id, student name)
        spec (dict): The test specification

    Returns:
        list: first entry is True/False for success.  If False, second
            entry is a string with an explanation.
    """

    log.info("ID prediction list uploaded")
    # do sanity check that the ID is in the classlist and the
    # test number is in range.
    ids = {int(X["id"]) for X in classlist}
    for test, sid in predictions:
        if int(sid) not in ids:
            return [False, f"ID {sid} not in classlist"]
        # TODO: Issue #1745: maybe check test is in database instead?
        if test < 0 or test > spec["numberToProduce"]:
            return [False, f"Test {test} outside range"]

    # now make a dict of id: [test,name] to push to database
    id_predictions = {}
    for test, sid in predictions:
        id_predictions[int(sid)] = [test]
    for X in classlist:
        if int(X["id"]) in id_predictions:
            id_predictions[int(sid)].append(X["name"])
    # now push everything into the DB
    raise NotImplementedError(
        "We have not decided what this operation should do with the old prediction list!  See Issue #2080"
    )
    problem_list = []
    for sid, test_and_name in id_predictions.items():
        # get the student_name from the classlist
        # TODO: probably we should only do this if current certainty less than 0.5
        # returns (True,None,None) or (False, 409, msg) or (False, 404, msg)
        r, what, msg = self.server.DB.add_or_change_id_prediction(
            test_and_name[0], sid, 0.5
        )
        if r:  # all good, continue pushing
            pass
        else:  # append the error to the problem list
            problem_list.append((what, msg))

    if problem_list:
        return [
            False,
            "Some predictions could not be saved to the database",
            problem_list,
        ]
    return [True, "All predictions saved to DB successfully"]


def IDreviewID(self, test_number):
    """Handle manager GUI's review of an ID'd paper.

    Args:
        test_number (str): ID reviewed test number.

    Returns:
        list: A list with a single True/False indicating
            if the review was successful.
    """

    return self.DB.IDreviewID(test_number)


def predict_id_lap_solver(self):
    """Predict IDs by matching unidentified papers against the classlist via linear assignment problem.

    Get the classlist and remove all people that are already IDed
    against a paper.  Get the list of unidentified papers.  Get the
    previously-computed probabilities of images being each digit.

    Probably some cannot be read: drop those from the list of unidenfied
    papers.

    Match the two.

    TODO: consider doing this client-side, although Manager tool would
    then depend on lapsolver or perhaps SciPy's linear_sum_assignment

    TODO: arguments to control which papers to run on...?

    Returns:
        str: status text, appropriate to show to a user.

    Raises:
        RuntimeError: id reader still running
        FileNotFoundError: no probability data
        IndexError: something is zero, degenerate assignment problem.
    """
    lock_file = specdir / "IDReader.lock"
    heatmaps_file = specdir / "id_prob_heatmaps.json"

    if lock_file.exists():
        _ = "ID reader lock present (still running?); cannot perform matching"
        log.info(_)
        raise RuntimeError(_)

    t = time.process_time()

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

    status += f"\nTime loading data: {time.process_time() - t:.02} seconds.\n"

    status += "\nBuilding cost matrix..."
    t = time.process_time()
    cost_matrix = assemble_cost_matrix(papers, sids, probabilities)
    status += f" done in {time.process_time() - t:.02} seconds.\n"

    status += "\nSolving assignment problem..."
    t = time.process_time()
    prediction_pairs = lap_solver(papers, sids, cost_matrix)
    status += f" done in {time.process_time() - t:.02} seconds."

    log.info("Wiping predictions by lap-solver")
    old_predictions = self.DB.ID_get_all_predictions()
    for papernum, v in old_predictions.items():  # v = (sid, certainty, predictor)
        if v[2] == "MLLAP":
            ok, code, msg = self.DB.remove_id_prediction(papernum)
            if not ok:
                raise RuntimeError(
                    f"Unexpectedly cannot find promised paper {papernum} in prediction DB"
                )
    # ------------------------ #
    # Maintain uniqueness in test and sid in the prediction list
    # our prediction_pairs should not (by construction) overlap with existing predictions on papernumber
    # but it might on SID - if an overlap in SID then remove from prediction_pairs and DB.
    # ------------------------ #
    log.info("Sanity check that no *paper numbers* from the prenamed are in LAP output")
    # 'predictions' only contains **non**MLLAP predictions
    predictions = self.DB.ID_get_all_predictions()
    for papernum, _ in prediction_pairs:
        # verify that there is no paper-number overlap between existing predictions
        # and those from MLLAP
        if papernum in predictions.keys():
            raise RuntimeError(
                f"Unexpectedly, found paper {papernum} in both LAP output and prename!"
            )
    # at this point the database and the prediction_pairs contain no overlaps in paper_number.
    # but we need to keep uniqueness in SID, so construct SID-lookup dict from existing predictions
    existing_sid_to_papernum = {predictions[X][0]: X for X in predictions}
    log.info("Saving prediction results into database /w certainty 0.5")
    errs = []
    for papernum, student_ID in prediction_pairs:
        # check if that SID is used in an existing prediction
        if student_ID in existing_sid_to_papernum:
            other_paper = existing_sid_to_papernum[student_ID]
            # delete from both the prediction_pairs and from the database.
            log.info(
                f"New prediction that {student_ID} wrote paper {papernum} conflicts with existing prediction of paper {other_paper}, so discarding both."
            )
            ok, code, msg = self.DB.remove_id_prediction(other_paper)
            if not ok:
                raise RuntimeError(
                    f"Unexpectedly cannot find promised paper {other_paper} in prediction DB"
                )
        else:  # is safe to add it to prediction list
            ok, code, msg = self.DB.add_or_change_id_prediction(
                papernum, student_ID, 0.5, predictor="MLLAP"
            )
            if not ok:
                # TODO: perhaps we want to decrease the prename confidence?  Or even delete it.
                # We may have detected student who should have been in the prename but wrote elsewhere
                errs.append(msg)
    if errs:
        status += "\n\nThe following LAP results where not used:\n"
        status += "  - " + "\n  - ".join(errs)

    return status


def run_id_reader(self, top, bottom, ignore_stamp):
    """Run the ML prediction model on the papers and saves the information.

    Args:
        top (float): where to crop in `[0, 1]`.
        bottom (float): where to crop in `[0, 1]`.
        ignore_stamp (bool): Whether to ignore the timestamp when
            deciding whether to skip the run.

    Returns:
        list: A list with first value boolean and second value boolean or a
        message string of the format:
        `[True, False]`: it is already running.
        `[False, str]`: prediction already exists, `str` is the
        timestamp of the last time prediction run.
        `[True, True]`: we started a new prediction run.
    """
    lock_file = specdir / "IDReader.lock"
    timestamp = specdir / "IDReader.timestamp"
    if os.path.isfile(lock_file):
        log.info("ID reader is already running.")
        return [True, False]

    # check the timestamp - unless manager tells you to ignore it.
    if os.path.isfile(timestamp):
        if ignore_stamp is False:
            with open(timestamp, "r") as fh:
                txt = json.load(fh)
            return [False, txt]
        else:
            os.unlink(timestamp)

    # get list of [test_number, image]
    log.info("ID get images for ID reader")
    test_image_dict = self.DB.IDgetImagesOfUnidentified()

    # Only mess with predictions that were created by MLLAP and not
    # any prenaming.
    predictions = self.DB.ID_get_all_predictions()
    # is dict {paper_number: (sid, certainty, who)}
    for k in list(test_image_dict.keys()):
        P = predictions.get(k, None)
        if P:
            # if the predictor for this test is "prename" then don't mess
            # with it. Remove it from the test image dictionary.
            # TODO - future this might be "prename" or "human"
            # so this will need changing to blah in ["prename", "human", "foo", ...]
            if P[2] == "prename":
                test_image_dict.pop(k)
                log.info(
                    'ID reader: drop test number "%s" b/c we think its prenamed', k
                )

    # dump this as json / lock_file for subprocess to use in background.
    with open(lock_file, "w") as fh:
        json.dump([test_image_dict, {"crop_top": top, "crop_bottom": bottom}], fh)
    # make a timestamp
    last_run_timestamp = datetime.now().strftime("%y:%m:%d-%H:%M:%S")

    with open(timestamp, "w") as fh:
        json.dump(last_run_timestamp, fh)

    # run the reader
    log.info("ID launch ID reader in background")

    # TODO - this is currently blocking I think.

    # Yuck, should at least check its running, Issue #862
    proc = subprocess.run(
        ["python3", "-m", "plom.server.run_the_predictor", lock_file],
        capture_output=True,
    )
    log.warn(f"Predicter subprocess.return code = {proc.returncode}")
    log.warn(f"Predicter subprocess.stdout = {proc.stdout.decode()}")
    log.warn(f"Predicter subprocess.stderr = {proc.stderr.decode()}")
    return [True, True]
