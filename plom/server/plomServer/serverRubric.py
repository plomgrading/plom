# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald,
# Copyright (C) 2021 Andrew Rechnitzer

"""
Rubric-related server methods.
"""

import logging


log = logging.getLogger("server")


def McreateRubric(self, username, new_rubric):
    """Get DB to create the new rubric element

    Args:
        username (str): the username making the new rubric
        rubric (dict): a dict containing the rubric info

    Returns:
        list: [True, new-key] or [False]
    """
    # check rubric sent has required fields
    if any(X not in new_rubric for X in ["delta", "text", "question", "tags", "meta"]):
        return [False]
    # else let DB create the new element and return the new key
    return self.DB.McreateRubric(username, new_rubric)


def MgetRubrics(self, question_number=None):
    """Get all rubrics in the DB and return as list of dict. If question is specified then get only rubrics for that question."""
    return self.DB.MgetRubrics(question_number)


def MmodifyRubric(self, username, key, updated_rubric):
    """Get DB to modify the rubric given by this key

    Args:
        username (str): the username making the new rubric
        key (str): the key of the rubric
        rubric (dict): a dict containing the rubric info

    Returns:
        list: [True, new-key] or [False]
    """
    # check rubric sent has required fields
    if any(
        X not in updated_rubric for X in ["delta", "text", "question", "tags", "meta"]
    ):
        return [False, "incomplete"]
    # else let DB modify the rubric and return the key.
    return self.DB.MmodifyRubric(username, key, updated_rubric)
