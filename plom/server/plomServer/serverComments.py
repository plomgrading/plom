# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald

import time
import json
import os
import logging
import copy
from pathlib import Path

from plom import specdir
from plom.comment_utils import generate_new_comment_ID


log = logging.getLogger("server")
path = Path(specdir) / "comments.json"


def _get_default_comments(number_of_questions):
    """Return the list of default comment dictionary.

    Args:
        number_of_questions (int): Number of questions in the exam.

    Returns:
        list: List of default comments dictionary objects.
    """

    comments_fields = [
        {"delta": -1, "text": "algebra"},
        {"delta": -1, "text": "arithmetic"},
        {"delta": ".", "text": "meh"},
        {"delta": 0, "text": r"tex: you can write \LaTeX, $e^{i\pi} + 1 = 0$"},
        {"delta": 0, "text": "be careful"},
        {"delta": 1, "text": "good", "meta": "give constructive feedback"},
    ]
    default_comments_fields = {
        "tags": "",
        "testname": "",
        "meta": "",
        "count": 0,
        "created": time.gmtime(0),
        "modified": time.gmtime(0),
        "username": "Administrator",
    }

    for d in comments_fields:
        for k, v in default_comments_fields.items():
            d.setdefault(k, default_comments_fields[k])

    comments_list = []
    # We need to create a version of the default comments for each question.
    for q_number in range(1, number_of_questions + 1):
        for comment in comments_fields:
            new_comment = copy.deepcopy(comment)
            new_comment["question_number"] = int(q_number)
            new_comment["id"] = generate_new_comment_ID()
            comments_list.append(new_comment)

    return comments_list


# TODO: Replace this with a method that connects to the database.
def MgetCurrentComments(self, username):
    """Load the current comments and send them back.

    If not json file for comments exist, create a new json file with
        the current comments.

    Args:
        username (str): User who created the comment.

    Returns:
        list: A list of the updated comments as dictionaries.
    """
    if os.path.isfile(path):
        with open(path, "r") as comments_file:
            existing_comments_list = json.load(comments_file)

        response_comments = existing_comments_list

        return response_comments
    else:
        current_comments = _get_default_comments(self.testSpec["numberOfQuestions"])
        with open(path, "w") as comments_file:
            json.dump(current_comments, comments_file)

        return current_comments


# TODO: Replace this with a method that connects to the database.
def MupdateCommentsCount(self, annotations):
    """Save incoming comments to json files and return the updated comments list.

    If not json file for comments exist, create a new json file with
        the current comments.
    If a new json file is created, all incoming comment annotations with
        IDs that don't exist in the json file are not counted.

    Args:
        annotations (list): A list of the annotations in the paper.

    Returns:
        list: A list of the updated comments as dictionaries.
    """
    annotated_comments = []
    for annotation in annotations:
        if len(annotation) > 2 and (annotation[0] == "GroupDeltaText"):
            annotated_comments.append(annotation)

    if os.path.isfile(path):
        with open(path, "r") as comments_file:
            existing_comments_list = json.load(comments_file)

        existing_comments_dictionary = {}
        for existing_comment in existing_comments_list:
            existing_comments_dictionary[existing_comment["id"]] = existing_comment

        for comment_in_paper in annotated_comments:
            if comment_in_paper[3] in existing_comments_dictionary.keys():
                existing_comments_dictionary[comment_in_paper[3]]["count"] += 1
            else:
                # If the comment does not exist in the database, TODO: Send an
                # error message or something. (at the moment, probably ignore the comment)
                print(
                    "Error: Comment with ID "
                    + str(comment_in_paper[3])
                    + " is not defined in te database."
                )
                print("Will not increase the comment count for this comment ID.")

        new_database_comments_list = list(existing_comments_dictionary.values())

        with open(path, "w") as comments_file:
            json.dump(new_database_comments_list, comments_file)

    else:
        current_comments = _get_default_comments(self.testSpec["numberOfQuestions"])

        existing_comments_dictionary = {}
        for existing_comment in current_comments:
            existing_comments_dictionary[existing_comment["id"]] = existing_comment

        for comment_in_paper in annotated_comments:
            if comment_in_paper[3] in existing_comments_dictionary.keys():
                existing_comments_dictionary[comment_in_paper[3]]["count"] += 1
            else:
                # If the comment does not exist in the database, TODO: Send an
                # error message or something. (at the moment, probably ignore the comment)
                print(
                    "Error: Comment with ID "
                    + str(comment_in_paper[3])
                    + " is not defined in te database."
                )
                print("Will not increase the comment count for this comment ID.")

        new_database_comments_list = list(existing_comments_dictionary.values())

        with open(path, "w") as comments_file:
            json.dump(new_database_comments_list, comments_file)

    return True


# TODO: Replace this with a method that connets to the database.
def MrefreshComments(self, username, current_marker_comments_list):
    """Save incoming comments to json files and return the updated comments list.

    Prioritize existing or default comments over new comments given by the users.
    Meaning if two comments have the same ID, keep the comments existing in the database.

    If not json file for this question's comments exist, create a new json file with
        the current comments.

    Args:
        username (str): A string including the username who made the comment.
        current_marker_comments_list (list): A list of the comments as dictionaries.

    Returns:
        list: A list of the existing comments.
    """
    # Add the new incoming comments to the database.
    # Over-write a comment with the same ID as any of the comments existing in the database.
    # Meaming we prioritize the existing comments over the incoming comments
    if os.path.isfile(path):
        with open(path, "r") as comments_file:
            existing_comments_list = json.load(comments_file)

        existing_comments_dictionary = {}
        for existing_comment in existing_comments_list:
            existing_comments_dictionary[existing_comment["id"]] = existing_comment

        for user_comment in current_marker_comments_list:
            if user_comment["id"] not in existing_comments_dictionary.keys():
                existing_comments_dictionary[user_comment["id"]] = user_comment

        new_database_comments_list = list(existing_comments_dictionary.values())
        response_comments = new_database_comments_list

        with open(path, "w") as comments_file:
            json.dump(new_database_comments_list, comments_file)

    else:
        # If the comments json for the database is not there, will be created.
        # Also, add the incoming comments.
        # Over-write a comment with the same ID as any of the default comment.
        # Meaming we prioritize the default comments over the incoming comments
        current_comments = _get_default_comments(self.testSpec["numberOfQuestions"])
        current_comment_IDs = [comment["id"] for comment in current_comments]

        for incoming_comment in current_marker_comments_list:
            if incoming_comment["id"] not in current_comment_IDs:
                current_comments.append(incoming_comment)
            else:
                # TODO A better error message I think.
                print(
                    "Error: There was a conflict regarding the comment ID "
                    + str(user_comment["id"])
                    + "."
                )
                print(
                    "Comments existing in the database are prioritized over incoming comments."
                )

        with open(path, "w") as comments_file:
            json.dump(current_comments, comments_file)
        response_comments = current_comments

    return response_comments
