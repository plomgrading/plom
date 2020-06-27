import hashlib
import logging
import os
import shutil
import uuid
from pathlib import Path
from datetime import datetime
import json
import subprocess
from plom import specdir

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
    """Respond with a list of image paths for an already ID'd paper.

    Args:
        username (str): Username requesting ID'd paper's image.
        test_number (str): Test ID number.

    Returns:
        list: True/False plus a list of the image paths for ID'd task.
    """

    return self.DB.IDgetImage(username, test_number)


def IDclaimThisTask(self, username, test_number):
    """Assign claimed task in database and send the images paths for claimed task.

    Args:
        username (str): Username claiming the task.
        test_number (str): Test ID number.

    Returns:
        list: True/False plus paths to the claimed task's images in the list.
    """
    # return [true, image-filename1, name2,...]
    # or return [false]
    return self.DB.IDgiveTaskToClient(username, test_number)


# TODO: These two functions seem the same.
def id_paper(self, *args, **kwargs):
    """Some glue between service routes and the database.

    TODO: according to documentation args and kwargs aren't supposed to have docs.
    Args:
        args (tuple): A tuple including test_number, TODO: upload_user, stuednt ID
            and student name.
        kwargs (dict): TODO ?

    Returns:
        list: A list including the results of the identification of 
            the paper on database. Examples are:
            (True, None, None) for success. 
            (False, 409, msg) for failure.
    """
    print("##############################")
    print("id_paper")
    print(type(args))
    print(args)
    print(type(kwargs))
    print(kwargs)
    print(type(self.DB.id_paper(*args, **kwargs)))
    print(self.DB.id_paper(*args, **kwargs))
    """Some glue between service routes and the database.

    See :func:`plom.db.db_create.id_paper` for details.
    """
    return self.DB.id_paper(*args, **kwargs)


def ID_id_paper(self, *args, **kwargs):

    print("##############################")
    print("ID_id_paper")
    print(type(kwargs))
    print(kwargs)

    return self.DB.ID_id_paper(*args, **kwargs)


def IDdidNotFinish(self, username, test_number):
    """Tell database to add unfinished ID'ing task to the todo pile.

    Args:
        username (str): Username with unfinished tasks.
        test_number (str): Test ID number.
    """

    self.DB.IDdidNotFinish(username, test_number)
    return


def IDgetImageFromATest(self):
    """Return all the images from an ID'ing task. TODO: How is this different
    why used with the prediction run. 

    Returns:
        list: True/False plus a list of the images' paths.
    """

    return self.DB.IDgetImageFromATest()


def IDdeletePredictions(self):
    """Delete the latest result from ID prediction/detection file.

    Log activity.

    Returns:
        list: A list with True/False which includes a message 
            string if the response is false.
    """

    # check to see if predictor is running
    lock_file = os.path.join(specdir, "IDReader.lock")
    if os.path.isfile(lock_file):
        log.info("ID reader currently running.")
        return [False, "ID reader is currently running"]

    # move old file out of way
    if not os.path.isfile(Path(specdir) / "predictionlist.csv"):
        return [False, "No prediction file present."]
    shutil.move(
        Path(specdir) / "predictionlist.csv", Path(specdir) / "predictionlist.bak"
    )
    with open(Path(specdir) / "predictionlist.csv", "w") as fh:
        fh.write("test, id\n")
    log.info("ID prediction list deleted")

    return [True]


def IDreviewID(self, test_number):
    """Handle manager GUI's review of an ID'd paper.

    Args:
        test_number (str): ID reviewed test number.

    Returns:
        list: A list with a single True/False indicating
            if the review was successful.
    """

    return self.DB.IDreviewID(test_number)


def IDrunPredictions(self, rectangle, file_number, ignore_stamp):
    """Run the ML prediction model on the papers and saves the information.

    Log activity.

    Args:
        rectangle (list): A list of coordinates if the format of:
            [top_left_x, top_left_y, bottom_right_x, bottom_right_y]
        file_number (int): Number of the file which the cropped rectangle was 
            extracted from. TODO: is this correct ?
        ignore_stamp (bool): To ignore or not to ignore the timestamp. TODO: is this correct ?

    Returns:
        list: A list with first value boolean and second value boolean or a 
            message string of the format:
            [True, False] for already running.
            [False, TODO: ?] for ?
            [True, True] for started running.
    """

    # from plom.server.IDReader.idReader import runIDReader
    lock_file = os.path.join(specdir, "IDReader.lock")
    timestamp = os.path.join(specdir, "IDReader.timestamp")
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
    test_image_dict = self.DB.IDgetImageByNumber(file_number)

    # dump this as json / lock_file for subprocess to use in background.
    with open(lock_file, "w") as fh:
        json.dump([test_image_dict, rectangle], fh)
    # make a timestamp
    last_run_timestamp = datetime.now().strftime("%y:%m:%d-%H:%M:%S")

    with open(timestamp, "w") as fh:
        json.dump(last_run_timestamp, fh)

    # run the reader

    log.info("ID launch ID reader in background")
    subprocess.Popen(["python3", "-m", "plom.server.IDReader.runTheReader", lock_file])
    return [True, True]
