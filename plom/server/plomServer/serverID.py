# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2022 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022-2023 Natalie Balashov

import csv
from datetime import datetime, timezone
import json
import logging
import subprocess
import time

from plom import specdir
from plom.idreader.assign_prob import lap_solver, greedy
from plom.misc_utils import datetime_to_json

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
        int/none: the next task number or None if no more.
    """
    return self.DB.IDgetNextTask()


def IDgetDoneTasks(self, username):
    """Return the list of already Id's papers by the user.

    Args:
        username (str): Username requesting done tasks.

    Returns:
        list: A list of list with sublists of the form
        `[paper_number, user_ID, username]`.
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


def add_or_change_predicted_id(self, *args, **kwargs):
    """Put/change a student id in database prediction table."""
    return self.DB.add_or_change_predicted_id(*args, **kwargs)


def remove_predicted_id(self, *args, **kwargs):
    """Remove a particular paper number from database prediction table."""
    return self.DB.remove_predicted_id(*args, **kwargs)


def ID_id_paper(self, *args, **kwargs):
    """Assign a student name/id combination to a paper in the database."""
    return self.DB.ID_id_paper(*args, **kwargs)


def IDgetImageFromATest(self):
    """Return a random front page exam image for ID box selection by the client.

    Returns:
        list: True/False plus a list of the images' paths.
    """
    return self.DB.IDgetImageFromATest()


def ID_get_predictions(self, *args, **kwargs):
    return self.DB.ID_get_predictions(*args, **kwargs)


def ID_delete_predictions(self, *args, **kwargs):
    return self.DB.ID_delete_predictions(*args, **kwargs)


def ID_put_predictions(self, predictions, predictor):
    """Push predictions to the database.

    Args:
        predictions (list): A list of pairs of (testnumber, student id)
        predictor (string): The predictor that generated the predictions

    Returns:
        tuple: first entry is True/False for success. If False, second
        entry is a string with an explanation.
    """
    log.info(f"Saving {predictor} prediction results into database w/ certainty")
    for papernum, student_ID, certainty in predictions:
        ok, code, msg = self.DB.add_or_change_predicted_id(
            papernum, student_ID, certainty=certainty, predictor=predictor
        )
        if not ok:
            return (False, f"Error occurred when saving predictions: {msg}")

    return (True, f"All {predictor} predictions saved to DB successfully.")


def IDreviewID(self, *args, **kwargs):
    return self.DB.IDreviewID(*args, **kwargs)


def get_sids_and_probabilities():
    """Retrieve student ID numbers from `classlist.csv` and probability data from `id_prob_heatmaps.json`.

    Returns:
        tuple: a 2-tuple consisting of two lists, where the first contains student ID numbers
               and the second contains the probability data

    Raises:
        RuntimeError: id reader still running
        FileNotFoundError: no probability data
    """
    lock_file = specdir / "IDReader.lock"
    heatmaps_file = specdir / "id_prob_heatmaps.json"

    if lock_file.exists():
        _ = "ID reader lock present (still running?); cannot perform matching"
        log.info(_)
        raise RuntimeError(_)

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


def id_reader_get_log(self):
    """Get the log for the running background ID reader process.

    Returns:
        list: A ``[is_running, time_stamp, partial_log]`` where
        ``is_running`` is a boolean whether the process is currently
        running, ``time_stamp`` is string for when the process started
        (in ISO 6801) or None if no process was ever started.
        ``partial_log`` is a string of the process's stdout and stderr;
        or None if no process was started (or perhaps if its started by
        no output written yet).
    """
    log_file = specdir / "IDReader.log"
    timestamp_file = specdir / "IDReader.timestamp"

    # TODO: need some mutex for thread safety around this variable?
    if not hasattr(self, "id_reader_proc"):
        self.id_reader_proc = None

    is_running = None
    if self.id_reader_proc:
        r = self.id_reader_proc.poll()
        if r is None:
            log.info("ID Reader process still running pid=%s", self.id_reader_proc.pid)
            is_running = True
        else:
            log.info(f"ID Reader process was running but stopped with code {r}")
            is_running = False

    try:
        with open(log_file, "r") as f:
            log_so_far = "".join(f.readlines())
    except FileNotFoundError:
        log_so_far = None

    timestamp = None
    if timestamp_file.exists():
        with open(timestamp_file, "r") as fh:
            timestamp = json.load(fh)
            log.info(f"Previous ID Reader process started at {timestamp}")

    return [is_running, timestamp, log_so_far]


def id_reader_run(self, top, bottom, *, ignore_timestamp=False):
    """Run the ML ID reader model on the papers and saves the information.

    Args:
        top (float): where to crop in `[0, 1]`.
        bottom (float): where to crop in `[0, 1]`.

    Keyword Args:
        ignore_timestamp (bool): Whether to ignore the timestamp when
            deciding whether to skip the run.

    Returns:
        list: of the form ``[is_running, new_job, time_stamp]`` where
        ``is_running`` is a boolean whether the process is currently
        running, ``new_job`` is boolean whether we just started a new
        job or not, and ``time_stamp`` is string for when the process
        started (in ISO 6801) or None if no process was ever started.
    """
    params_file = specdir / "IDReader.json"
    log_file = specdir / "IDReader.log"
    timestamp_file = specdir / "IDReader.timestamp"

    # TODO: need some mutex for thread safety around this variable?
    if not hasattr(self, "id_reader_proc"):
        self.id_reader_proc = None

    is_running = None
    if self.id_reader_proc:
        r = self.id_reader_proc.poll()
        if r is None:
            log.info("ID Reader process still running pid=%s", self.id_reader_proc.pid)
            is_running = True
        else:
            log.info(f"ID Reader process was running but stopped with code {r}")
            is_running = False

    timestamp = None
    if timestamp_file.exists():
        with open(timestamp_file, "r") as fh:
            timestamp = json.load(fh)
            log.info(f"Previous ID Reader process started at {timestamp}")

    new_start = False

    # normally we stop if running or if timestamp exists but both
    # can be overridden
    if is_running:
        return [is_running, new_start, timestamp]
    elif timestamp:
        if not ignore_timestamp:
            return [is_running, new_start, timestamp]

    # we're launching a new job
    new_start = True

    # get list of [test_number, image]
    log.info("ID get images for ID reader")
    test_image_dict = self.DB.IDgetImagesOfUnidentified()

    # Only mess with predictions that were created by MLLAP and not
    # any prenaming.
    predictions = self.DB.ID_get_predictions(predictor="prename")
    # is dict {paper_number: (sid, certainty, who)}
    for k in list(test_image_dict.keys()):
        P = predictions.get(k, None)
        if P:
            # TODO: future may need in ["prename", "human", ...]
            # Don't try to read IDs from prenamed papers
            test_image_dict.pop(k)
            log.info('ID reader: drop test number "%s" b/c we think its prenamed', k)

    # dump this as parameters_file for subprocess to use in background.
    with open(params_file, "w") as fh:
        json.dump([test_image_dict, {"crop_top": top, "crop_bottom": bottom}], fh)

    log.info("launch ID reader in background")
    timestamp = datetime_to_json(datetime.now(timezone.utc))

    with open(timestamp_file, "w") as fh:
        json.dump(timestamp, fh)

    # TODO: I hope close_fds=True implies this will be closed
    _fd = open(log_file, "w")
    self.id_reader_proc = subprocess.Popen(
        ["python3", "-u", "-m", "plom.server.run_the_predictor", params_file],
        stdout=_fd,
        stderr=subprocess.STDOUT,
        close_fds=True,
        text=True,
    )

    try:
        self.id_reader_proc.wait(timeout=0.25)
    except subprocess.TimeoutExpired:
        pass

    return [True, new_start, timestamp]


def id_reader_kill(self):
    """Kill any running machine ID reader.

    Returns:
        tuple: ``(bool, str)``, True if it wasn't running or stopped
        when asked, False if things got messy.  The string is a
        human-readable explanation.
    """
    # TODO: need some mutex for thread safety around this variable?
    if not hasattr(self, "id_reader_proc"):
        self.id_reader_proc = None

    if self.id_reader_proc is None:
        return (True, "Process was not running")

    pid = self.id_reader_proc.pid
    try:
        self.id_reader_proc.wait(timeout=0.1)
    except subprocess.TimeoutExpired:
        pass
    else:
        return (True, f"Process {pid} was already stopped")

    log.info("ID Reader process %s: asking politely to stop", pid)
    self.id_reader_proc.kill()
    try:
        self.id_reader_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    else:
        self.id_reader_proc = None
        log.info("Process %s stopped within 5 seconds", pid)
        return (True, f"Process {pid} stopped within 5 seconds")

    # now we insist
    self.id_reader_proc.terminate()
    log.info("ID Reader process %s: insisting (SIGTERM) that it stop...", pid)
    try:
        self.id_reader_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    else:
        self.id_reader_proc = None
        log.info("Process %s stopped within 10 seconds of SIGTERM", pid)
        return (True, f"Process {pid} stopped within 10 seconds of SIGTERM")

    log.info("ID Reader process %s: did not stop when asked too, leaving zombie", pid)
    self.id_reader_proc = None
    return (False, f"Process {pid} has likely become a zombie: talk to server admin")
