# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald

import random
import time
import copy


def generate_new_comment_ID(num_of_digits=12):
    """Generate a random number string as a new comment ID.

    Args:
        num_of_digits (int, optional): Number of digits for comment ID.
            Defaults to 12.

    Returns:
        str: A 12 digit number as a string representing the new comment
            ID.
    """
    # TODO: Why string you ask ? Well because of this:
    # comIDi = QStandardItem(com["id"])
    # OverflowError: argument 1 overflowed: value must be in the range -2147483648 to 2147483647
    return str(random.randint(10 ** num_of_digits, 10 ** (num_of_digits + 1) - 1))


def comments_apply_default_fields(comlist):
    """Add missing fields with defaults to list of comments.

    Args:
        comlist (list): list of dicts.  Copies will not be made so
            keep a deep copy if you need the original.

    Returns:
        list: updated list of dicts.
    """
    comment_defaults = {
        "tags": "",
        "testname": "",
        "meta": "",
        "count": 0,
        "created": time.gmtime(0),
        "modified": time.gmtime(0),
        "username": "Administrator",
    }
    for d in comlist:
        for k, v in comment_defaults.items():
            d.setdefault(k, comment_defaults[k])
    return comlist


# TODO: useful in whatever code initializes the rubric DB?
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
