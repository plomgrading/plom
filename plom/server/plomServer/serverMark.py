# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2021 Andrew Rechnitzer
# Copyright (C) 2020-2023 Colin B. Macdonald
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2022 Chris Jin

import hashlib
import json
import os
import logging

from plom.textools import texFragmentToPNG
from plom.tagging import is_valid_tag_text as _is_valid_tag_text


log = logging.getLogger("server")


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
        list: with two integers, indicating the number of questions
        graded and the total number of questions to be graded of
        this question-version pair.
    """
    # TODO: consider refactoring McountMarked/McountAll to raise these instead
    if question_number < 1 or question_number > self.testSpec["numberOfQuestions"]:
        raise ValueError("Question number out of range.")
    if version_number < 1 or version_number > self.testSpec["numberOfVersions"]:
        raise ValueError("Version number out of range.")
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
        `[question_code string, maximum_mark, question_grade, [list of tag_texts]]`.
    """
    version_number = int(version_number)
    question_number = int(question_number)
    return self.DB.MgetDoneTasks(username, question_number, version_number)


def MgetNextTask(self, *args, **kwargs):
    return self.DB.MgetNextTask(*args, **kwargs)


def MlatexFragment(self, latex_fragment):
    """Respond with image data for a rendered latex of a text fragment.

    Args:
        latex_fragment (str): The string to be rendered.

    Returns:
        tuple: `(True, imgdata)`, or `(False, error_message)`.
    """
    return texFragmentToPNG(latex_fragment)


def MclaimThisTask(self, *args, **kwargs):
    return self.DB.MgiveTaskToClient(*args, **kwargs)


def MreturnMarkedTask(
    self,
    username,
    task_code,
    question_number,
    version_number,
    mark,
    annot_img_bytes,
    annot_img_type,
    plomdat,
    rubrics,
    time_spent_marking,
    annotated_image_md5,
    integrity_check,
    images_used,
):
    """Save the marked paper's information to database and respond with grading progress.

    Args:
        username (str): User who marked the paper.
        task_code (str): Code string for the task.
        question_number (int): Marked question number.
        version_number (int): Marked question version number.
        mark (int): Question mark.
        annot_img_bytes (bytearray): Marked image of question.  Currently
            accepts jpeg or png.
        annot_img_type (str): extension "jpg" or "png".
        plomdat (bytearray): Plom data file used for saving marking information in
            editable format.   TODO: should be json?
        rubrics (list[str]): Return the list of rubric IDs used
        time_spent_marking (int): Seconds spent marking the paper.
        annotated_image_md5 (str): MD5 hash of the annotated image.
        integrity_check (str): the integrity_check string for this task
        images_used (list[dict]): list of images used, with keys "md5"
            and "id" (and optionally other keys that we don't use).

    Returns:
        list: Respond with a list which includes:
        `[False, error_msg]`, either mismatching codes or database owning the task,
        `[True, number of graded tasks, total number of tasks]`.
    """
    # do sanity checks on incoming annotation image file
    md5 = hashlib.md5(annot_img_bytes).hexdigest()
    if md5 != annotated_image_md5:
        errstr = f"Checksum mismatch: annotated image data has {md5} but client said {annotated_image_md5}"
        log.error(errstr)
        return [False, errstr]

    annot_img_filename = f"markedQuestions/G{task_code[1:]}.{annot_img_type}"

    # Sanity check the plomfile
    # currently it comes as bytes, although we should refactor this
    try:
        plomdat = plomdat.decode()
    except UnicodeDecodeError as e:
        return [False, f"Invalid JSON in plom json data: {str(e)}"]
    # TODO: ok to read plomdat twice?  Maybe save the json later
    try:
        plom_data = json.loads(plomdat)
    except json.JSONDecodeError as e:
        return [False, f"Invalid JSON in plom json data: {str(e)}"]
    if plom_data.get("currentMark") != mark:
        return [False, f"Mark mismatch: {mark} does not match plomfile content"]
    for x, y in zip(images_used, plom_data["base_images"]):
        if x["md5"] != y["md5"]:
            errstr = (
                "data mismatch: base image md5s do not match plomfile: "
                + f'{images_used} versus {plom_data["base_images"]}'
            )
            return [False, errstr]

    # now update the database
    database_task_response = self.DB.MtakeTaskFromClient(
        task_code,
        username,
        mark,
        annot_img_filename,
        plomdat,
        rubrics,
        time_spent_marking,
        annotated_image_md5,
        integrity_check,
        images_used,
    )

    if database_task_response[0] is False:
        return database_task_response

    # db successfully updated
    #  check if those files exist already - back up if so
    for filename in (annot_img_filename,):
        if os.path.isfile(filename):
            # start with suffix 0 and keep incrementing until get a safe suffix.
            suffix = 0
            while True:
                newname = filename + f".rgd.{suffix}"
                if os.path.isfile(newname):
                    suffix += 1
                else:
                    break
            os.rename(filename, newname)

    # now write in the files
    with open(annot_img_filename, "wb") as file_header:
        file_header.write(annot_img_bytes)

    # return ack with current counts.
    return [
        True,
        (
            self.DB.McountMarked(question_number, version_number),
            self.DB.McountAll(question_number, version_number),
        ),
    ]


def is_valid_tag_text(self, tag_text):
    return _is_valid_tag_text(tag_text)


def MgetAllTags(self):
    return self.DB.MgetAllTags()


def MgetTagsOfTask(self, task):
    return self.DB.MgetTagsOfTask(task)


def McheckTagKeyExists(self, tag_key):
    return self.DB.McheckTagKeyExists(tag_key)


def McheckTagTextExists(self, tag_text):
    return self.DB.McheckTagTextExists(tag_text)


def McreateNewTag(self, username, tag_text):
    return self.DB.McreateNewTag(username, tag_text)


def add_tag(self, username, task, tag_text):
    """Assign a tag to a paper.

    Args:
        username (str): User who is assigning tag to the paper.
            TODO: currently not recorded but likely we want to record this.
        task (str): Code string for the task (paper).
        tag_text (str): Text of tag to assign to the paper.

    Returns:
        bool: True if tag was set in database successfully if the tag
        was already set.  False if no such paper or other error.
    """
    # do sanity check of the tag-text
    if self.DB.McheckTagTextExists(tag_text) is False:
        log.warning(f'tag with text "{tag_text}" does not exist - creating it now.')
        self.DB.McreateNewTag(username, tag_text)

    return self.DB.MaddExistingTag(username, task, tag_text)


def remove_tag(self, *args, **kwargs):
    return self.DB.MremoveExistingTag(*args, **kwargs)


def get_pagedata(self, *args, **kwargs):
    return self.DB.getAllTestImages(*args, **kwargs)


def get_pagedata_question(self, *args, **kwargs):
    return self.DB.getQuestionImages(*args, **kwargs)


def get_pagedata_context_question(self, *args, **kwargs):
    return self.DB.MgetWholePaper(*args, **kwargs)


def MreviewQuestion(self, *args, **kwargs):
    return self.DB.MreviewQuestion(*args, **kwargs)


def MrevertTask(self, *args, **kwargs):
    return self.DB.MrevertTask(*args, **kwargs)
