# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald

"""
Comment-related server methods.

  * TODO: not threadsafe, keeps read/writing the same file.
    But I think aiohttp will call this from different threads.
  * TODO: replace with database?
"""

import json
import logging
import copy
from pathlib import Path

from plom import specdir
from plom.comment_utils import generate_new_comment_ID, comments_apply_default_fields


log = logging.getLogger("server")
comfile = Path(specdir) / "comments.json"


def _get_default_comments(number_of_questions):
    """Return the list of default comment dictionary.

    Args:
        number_of_questions (int): Number of questions in the exam.

    Returns:
        list: List of default comments dictionary objects.
    """

    comlist0 = [
        {"delta": -1, "text": "algebra"},
        {"delta": -1, "text": "arithmetic"},
        {"delta": ".", "text": "meh"},
        {"delta": 0, "text": r"tex: you can write \LaTeX, $e^{i\pi} + 1 = 0$"},
        {"delta": 1, "text": "good", "meta": "give constructive feedback"},
    ]
    comlist0 = comments_apply_default_fields(comlist0)

    comments_list = []
    # We need to create a version of the default comments for each question.
    for q_number in range(1, number_of_questions + 1):
        for comment in comlist0:
            new_comment = copy.deepcopy(comment)
            new_comment["question_number"] = int(q_number)
            new_comment["id"] = generate_new_comment_ID()
            comments_list.append(new_comment)

    return comments_list


def _get_current_comment_list(numquestions):
    if comfile.is_file():
        with open(comfile, "r") as f:
            comments = json.load(f)
    else:
        comments = _get_default_comments(numquestions)
        with open(comfile, "w") as f:
            json.dump(comments, f)
    return comments


def _get_current_comment_dict(numquestions):
    comment_list = _get_current_comment_list(numquestions)
    comment_dict = {}
    for c in comment_list:
        comment_dict[c["id"]] = c
    return comment_dict


def MgetCurrentComments(self, username=None):
    """Load the current comments and send them back.

    If no json file for comments exists, create a new json file.

    Args:
        username (str): a username, currently unused and defaults to
            None.  In future might return only relevant comments.

    Returns:
        list: the current comments as a list of dicts.
    """
    return _get_current_comment_list(self.testSpec["numberOfQuestions"])


def MupdateCommentsCount(self, annotations):
    """Update the counts of any comments that appear in a list of annotations.

    Any comment ID that does not exist in the current DB is not counted.

    Args:
        annotations (list): A list of the annotations in the paper.

    Returns:
        bool: for now, always True.
    """
    comments_dict = _get_current_comment_dict(self.testSpec["numberOfQuestions"])

    # filter out non-comments
    annotated_comments = []
    for annotation in annotations:
        if len(annotation) > 2 and (annotation[0] == "GroupDeltaText"):
            annotated_comments.append(annotation)

    for comment_in_paper in annotated_comments:
        cid = comment_in_paper[3]
        if cid in comments_dict.keys():
            comments_dict[cid]["count"] += 1
        else:
            log.error(
                "Comment ID {} not in database, cannot increase count".format(cid)
            )

    comments_list = list(comments_dict.values())
    with open(comfile, "w") as f:
        json.dump(comments_list, f)
    return True


def MrefreshComments(self, username, current_marker_comments_list):
    """Add incoming comments to database and return the updated comments list.

    New comments with existing IDs silently overwrite the old comment in
    the database.  TODO: is this what we want?

    Args:
        username (str): A string including the username who made the
            comment.  TODO: currently unused.
        current_marker_comments_list (list): A list of the comments as dictionaries.
            TODO: is this the list on the page or is it the clients
            local list?  routesMark.py makes it sound like latter.

    Returns:
        list: newly updated comments as list of dicts.
    """
    comments_dict = _get_current_comment_dict(self.testSpec["numberOfQuestions"])

    for user_comment in current_marker_comments_list:
        if user_comment["id"] not in comments_dict.keys():
            # TODO: note overwrites old comment with new one
            comments_dict[user_comment["id"]] = user_comment

    comments_list = list(comments_dict.values())
    with open(comfile, "w") as f:
        json.dump(comments_list, f)
    return comments_list
