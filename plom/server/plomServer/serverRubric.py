# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald,
# Copyright (C) 2021 Andrew Rechnitzer

"""
Rubric-related server methods.
"""

import json
import logging
import os

log = logging.getLogger("server")


def McreateRubric(self, username, new_rubric):
    """Get DB to create the new rubric element

    Args:
        username (str): the username making the new rubric
        rubric (dict): a dict containing the rubric info

    Returns:
        tuple: `(True, key)` or `(False, err_msg)`.
    """
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
        tuple: `(True, new_key)` or `(False, err_msg)`.
    """
    return self.DB.MmodifyRubric(username, key, updated_rubric)


def MgetUserRubricPanes(self, username, question):
    try:
        paneConfigFilename = os.path.join(
            "userRubricPaneData", "rubricPanes.{}.{}.json".format(username, question)
        )
        if os.path.isfile(paneConfigFilename):
            pass
        else:
            return [False]
        with open(paneConfigFilename) as infile:
            rubricPanes = json.load(infile)
        return [True, rubricPanes]
    except:
        return [False]


def MsaveUserRubricPanes(self, username, question, rubricPanes):
    try:
        paneConfigFilename = os.path.join(
            "userRubricPaneData", "rubricPanes.{}.{}.json".format(username, question)
        )
        with open(paneConfigFilename, "w") as outfile:
            json.dump(rubricPanes, outfile)
        return True
    except:
        return False
