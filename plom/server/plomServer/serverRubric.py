# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021 Colin B. Macdonald,
# Copyright (C) 2021 Andrew Rechnitzer

"""
Rubric-related server methods.
"""

import json
import logging
from pathlib import Path


log = logging.getLogger("server")

rubric_cfg_dir = Path("userRubricPaneData")


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
    panefile = rubric_cfg_dir / "rubricPanes.{}.{}.json".format(username, question)
    if not panefile.exists():
        return [False]
    with open(panefile) as f:
        rubricPanes = json.load(f)
    return [True, rubricPanes]


def MsaveUserRubricPanes(self, username, question, rubricPanes):
    panefile = rubric_cfg_dir / "rubricPanes.{}.{}.json".format(username, question)
    with open(panefile, "w") as f:
        json.dump(rubricPanes, f)


def RgetTestRubricMatrix(self):
    return self.DB.Rget_test_rubric_count_matrix()


def RgetRubricCounts(self):
    return self.DB.Rget_rubric_counts()


def RgetRubricDetails(self, key):
    return self.DB.Rget_rubric_details(key)
