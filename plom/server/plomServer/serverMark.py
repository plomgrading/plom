# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian

from datetime import datetime
import hashlib
import imghdr
import json
import os
import subprocess
import tempfile
import uuid
import logging

from plom.textools import texFragmentToPNG


log = logging.getLogger("server")


def MgetQuestionMax(self, question_number, version_number):
    """Return the maximum score for the question.

    Args:
        question_number (int): Question number.
        version_number (int): Version number.

    Returns:
        list: A list where the first element is a boolean operation
            status response. The second element is either a string
            indicating if question fo version number is incorrect, or,
            the maximum score for this question as an integer.
    """

    version_number = int(version_number)
    question_number = int(question_number)
    # check question /version in range.
    if question_number < 1 or question_number > self.testSpec["numberOfQuestions"]:
        return [False, "QE"]
    if version_number < 1 or version_number > self.testSpec["numberOfVersions"]:
        return [False, "VE"]
    # Send back the max-mark for that question_number/version_number
    return [True, self.testSpec["question"][str(question_number)]["mark"]]


def MgetAllMax(self):
    """Get the maximum mark for each question in the exam.

    Returns:
        dict: A dictionary of the form {key: question_number, value: question_max_grade}
            for the exam questions.
    """

    max_grades = {}
    for q_number in range(1, self.testSpec["numberOfQuestions"] + 1):
        max_grades[q_number] = self.testSpec["question"][str(q_number)]["mark"]
    return max_grades


def MprogressCount(self, question_number, version_number):
    """Send back the marking progress count for question.

    Args:
        question_number (int): Question number.
        version_number (int): Version number.

    Returns:
        list: A list of two integers indicating the number of questions graded
            and the total number of assigned question to be graded of this question number
            and question version.
    """

    version_number = int(version_number)
    question_number = int(question_number)
    return [
        self.DB.McountMarked(question_number, version_number),
        self.DB.McountAll(question_number, version_number),
    ]


def MgetDoneTasks(self, username, question_number, version_number):
    """Respond with a list of the graded tasks.

    Args:
        username (str): Username string.
        question_number (int): Question number.
        version_number (int): Version number.

    Returns:
        list: Respond with a list of done tasks, each list includes
            [question_code string, maximum_mark, question_grade, question_tag string].
    """

    version_number = int(version_number)
    question_number = int(question_number)
    return self.DB.MgetDoneTasks(username, question_number, version_number)


def MgetNextTask(self, question_number, version_number):
    """Retrieve the next unmarked paper from the database.

    Args:
        question_number (int): Next question's question number.
        version_number (int): Next question's version number.

    Returns:
        list: Respond with a list with either value False or the value
            of True with the question code string for next task.
    """

    give = self.DB.MgetNextTask(question_number, version_number)
    if give is None:
        return [False]
    else:
        return [True, give]


def MlatexFragment(self, username, latex_fragment):
    """Respond with a path to the latex fragment image.

    Args:
        username (str): Username string.
        latex_fragment (str): The latex string for the latex image requested.

    Returns:
        list: A list with either False or True with the latex image's
            file name.
    """

    # TODO - only one frag file per user - is this okay?
    filename = os.path.join(self.tempDirectory.name, "{}_frag.png".format(username))

    if texFragmentToPNG(latex_fragment, filename):
        return [True, filename]
    else:
        return [False]


def MclaimThisTask(self, username, task_code):
    """Assign the specified paper to this user and return the task information.

    Args:
        username (str): User who requests the paper.
        task_code (str): Code string for the claimed task.

    Returns:
        list: A list which either only has a False value included or
            [True, `question_tag`, `integrity_check`, `list_of_image_md5s` `image_file1`, `image_file2`,...]
    """

    return self.DB.MgiveTaskToClient(username, task_code)


def MdidNotFinish(self, username, task_code):
    """Inform database that a user did not finish a task.

    Args:
        username (str): Owner of the unfinished task.
        task_code (str): Code string for the unfinished task.
    """

    self.DB.MdidNotFinish(username, task_code)
    return


# TODO: As input to MreturnMarkedTask, the comments string is in a
# list ie `["comment 1", "comment 2", "comment 3"]`
# Maybe this should be changed.
def MreturnMarkedTask(
    self,
    username,
    task_code,
    question_number,
    version_number,
    mark,
    image,
    plomdat,
    comments,
    time_spent_marking,
    tags,
    md5_code,
    integrity_check,
    image_md5s,
):
    """Save the marked paper's information to database and respond with grading progress.

    Args:
        username (str): User who marked the paper.
        task_code (str): Code string for the task.
        question_number (int): Marked queston number.
        version_number (int): Marked question version number.
        mark (int): Question mark.
        image (bytearray): Marked image of question.
        plomdat (bytearray): Plom data file used for saving marking information in
            editable format.
        comments (str): Return the String of the comments list.
        time_spent_marking (int): Seconds spent marking the paper.
        tags (str): Tag assigned to the paper.
        md5_code (str): MD5 hash key for this task.
        integrity_check (str): the integrity_check string for this task
        image_md5s (list[str]): list of image md5sums used.


    Returns:
        list: Respond with a list which includes:
            [False, Error message of either mismatching codes or database owning the task.]
            [True, number of graded tasks, total number of tasks.]
    """

    # TODO: score + file sanity checks were done at client. Do we need to redo here?
    # image, plomdat are bytearrays, comments = list
    annotated_filename = "markedQuestions/G{}.png".format(task_code[1:])
    plom_filename = "markedQuestions/plomFiles/G{}.plom".format(task_code[1:])
    comments_filename = "markedQuestions/commentFiles/G{}.json".format(task_code[1:])

    # do sanity checks on incoming annotation image file
    # Check the annotated_filename is valid png - just check header presently
    # notice that 'imghdr.what(name, h=blah)' ignores the name, instead checks stream blah.
    if imghdr.what(annotated_filename, h=image) != "png":
        log.error(
            "Uploaded annotation file is not a PNG. Instead is = {}".format(
                imghdr.what(annotated_filename, h=image)
            )
        )
        return [False, "Misformed image file. Try again."]

    # Also check the md5sum matches
    md5n = hashlib.md5(image).hexdigest()
    if md5_code != md5n:
        log.error(
            "Mismatched between client ({}) and server ({}) md5sums of annotated image.".format(
                md5_code, md5n
            )
        )
        return [
            False,
            "Misformed image file - md5sum doesn't match serverside={} vs clientside={}. Try again.".format(
                md5n, md5_code
            ),
        ]

    # now update the database
    database_task_response = self.DB.MtakeTaskFromClient(
        task_code,
        username,
        mark,
        annotated_filename,
        plom_filename,
        comments_filename,
        time_spent_marking,
        tags,
        md5n,
        integrity_check,
        image_md5s,
    )

    if database_task_response[0] is False:
        return database_task_response

    # db successfully updated
    #  check if those files exist already - back up if so
    for filename in [annotated_filename, plom_filename, comments_filename]:
        if os.path.isfile(filename):
            os.rename(
                filename,
                filename + ".rgd" + datetime.now().strftime("%d_%H-%M-%S"),
            )

    # now write in the files
    with open(annotated_filename, "wb") as file_header:
        file_header.write(image)
    with open(plom_filename, "wb") as file_header:
        file_header.write(plomdat)
    with open(comments_filename, "w") as file_header:
        json.dump(comments, file_header)

    self.MrecordMark(username, mark, annotated_filename, time_spent_marking, tags)
    # return ack with current counts.
    return [
        True,
        self.DB.McountMarked(question_number, version_number),
        self.DB.McountAll(question_number, version_number),
    ]


def MrecordMark(self, username, mark, annotated_filename, time_spent_marking, tags):
    """Saves the marked paper information as a backup, independent of the server

    Args:
        username (str): User who marked the paper.
        mark (int): Question mark.
        annotated_filename (str): Name of the annotated image file.
        time_spent_marking (int): Seconds spent marking the paper.
        tags (str): Tag assigned to the paper.
    """

    with open("{}.txt".format(annotated_filename), "w") as file_header:
        file_header.write(
            "{}\t{}\t{}\t{}\t{}\t{}".format(
                annotated_filename,
                mark,
                username,
                datetime.now().strftime("%Y-%m-%d,%H:%M"),
                time_spent_marking,
                tags,
            )
        )


def MgetImages(self, username, task_code, integrity_check):
    """Respond with paths to the marked and original images of a marked question.

    Args:
        username (str): User who marked the paper.
        task_code (str): Code string for the task.
        integrity_check (str): Integrity check string for the task.

    Returns:
        list: A list of the format:
            [False, Error message string.]
            [True, Number of papers in the question, md5 list, Original images paths,
            Annotated image path, Plom data file for this page]
    """

    return self.DB.MgetImages(username, task_code, integrity_check)


# TODO: Have to figure this out.  Please needs documentation.
def MgetOriginalImages(self, task):
    return self.DB.MgetOriginalImages(task)


def MsetTag(self, username, task_code, tag):
    """Assign a tag string to a paper

    Args:
        username (str): User who assigned tag to the paper.
        task_code (str): Code string for the task.
        tags (str): Tag assigned to the paper.

    Returns:
        bool: True or False indicating if tag was set in database successfully.
    """

    return self.DB.MsetTag(username, task_code, tag)


def MgetWholePaper(self, test_number, question_number):
    """Respond with all the images of the paper including the given question.

    Args:
        test_number (str): A string which has the test number in the format `0011`
            for example.
        question_number (str): Question number.

    Returns:
        list: A list including the following information:
            Boolean of wether we got the paper images.
            A list of lists including [`test_version`, `image_md5sum_list`, `does_page_belong_to_question`].
            Followed by a series of image paths for the pages of the paper.
    """

    return self.DB.MgetWholePaper(test_number, question_number)


def MreviewQuestion(self, test_number, question_number, version_number):
    """Save question results in database.

    Args:
        test_number (int): Reviewed test number.
        question_number (int): Review queston number.
        version_number (int): Marked question version number.

    Returns:
        list: Respond with a list with value of either True or False.
    """

    return self.DB.MreviewQuestion(test_number, question_number, version_number)


# TODO: Deprecated.
# TODO: Should be removed.
def MrevertTask(self, code):
    rval = self.DB.MrevertTask(code)
    # response is [False, "NST"] or [False, "NAC"] or [True]
    return rval
