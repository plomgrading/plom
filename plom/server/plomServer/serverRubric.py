# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Vala Vakilian
# Copyright (C) 2021-2023 Colin B. Macdonald,
# Copyright (C) 2021 Andrew Rechnitzer

"""
Rubric-related server methods.
"""

import json
import logging
from pathlib import Path


log = logging.getLogger("server")

rubric_cfg_dir = Path("userRubricPaneData")


def McreateRubric(self, *args, **kwargs):
    """Get DB to create the new rubric element."""
    return self.DB.McreateRubric(*args, **kwargs)


def MgetRubrics(self, *args, **kwargs):
    """Get all rubrics in the DB and return as list of dict. If question is specified then get only rubrics for that question."""
    return self.DB.MgetRubrics(*args, **kwargs)


def MmodifyRubric(self, *args, **kwargs):
    """Get DB to modify the rubric given by this key."""
    return self.DB.MmodifyRubric(*args, **kwargs)


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
