# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer

"""
Solution-related server methods.
"""

import json
import logging
import os
import hashlib

log = logging.getLogger("server")


def getSolutionStatus(self):
    status = {}
    for q in range(1, self.server.testSpec.numberOfQuestions + 1):
        if self.server.testSpec["question.{}".format(q)]["select"] == "shuffle":
            vm = self.server.testSpec.numberOfVersions
        else:
            vm = 1
        for v in range(1, vm + 1):
            solutionFile = os.path.join(
                "solutionImages", "solution.{}.{}.png".format(q, v)
            )
            if os.path.isfile(solutionFile):
                # check the md5sum and return it.
                with open(solutionFile, "rb") as fh:
                    img_obj = fh.read()
                    status[(q, v)] = hashlib.md5(img_obj).hexdigest()
            else:  # else return empty string
                status[(q, v)] = ""
    return status


def getSolutionImage(self, question, version):
    solutionFile = os.path.join(
        "solutionImages", "solution.{}.{}.png".format(question, version)
    )
    if os.path.isfile(solutionFile):
        return solutionFile
    else:
        return None


def uploadSolutionImage(self, question, version, md5sum, image):
    # check md5sum matches
    md5n = hashlib.md5(image).hexdigest()
    if md5n != md5sum:
        return False

    solutionFile = os.path.join(
        "solutionImages", "solution.{}.{}.png".format(question, version)
    )
    with open(solutionFile, "wb") as fh:
        fh.write(image)
    return True


#
# def McreateRubric(self, username, new_rubric):
#     """Get DB to create the new rubric element
#
#     Args:
#         username (str): the username making the new rubric
#         rubric (dict): a dict containing the rubric info
#
#     Returns:
#         list: [True, new-key] or [False]
#     """
#     # check rubric sent has required fields
#     if any(X not in new_rubric for X in ["delta", "text", "question", "tags", "meta"]):
#         return [False]
#     # else let DB create the new element and return the new key
#     return self.DB.McreateRubric(username, new_rubric)
#
#
# def MgetRubrics(self, question_number=None):
#     """Get all rubrics in the DB and return as list of dict. If question is specified then get only rubrics for that question."""
#     return self.DB.MgetRubrics(question_number)
#
#
# def MmodifyRubric(self, username, key, updated_rubric):
#     """Get DB to modify the rubric given by this key
#
#     Args:
#         username (str): the username making the new rubric
#         key (str): the key of the rubric
#         rubric (dict): a dict containing the rubric info
#
#     Returns:
#         list: [True, new-key] or [False]
#     """
#     # check rubric sent has required fields
#     if any(
#         X not in updated_rubric for X in ["delta", "text", "question", "tags", "meta"]
#     ):
#         return [False, "incomplete"]
#     # else let DB modify the rubric and return the key.
#     return self.DB.MmodifyRubric(username, key, updated_rubric)
#
#
# def MgetUserRubricPanes(self, username, question):
#     try:
#         paneConfigFilename = os.path.join(
#             "userRubricPaneData", "rubricPanes.{}.{}.json".format(username, question)
#         )
#         if os.path.isfile(paneConfigFilename):
#             pass
#         else:
#             return [False]
#         with open(paneConfigFilename) as infile:
#             rubricPanes = json.load(infile)
#         return [True, rubricPanes]
#     except:
#         return [False]
#
#
# def MsaveUserRubricPanes(self, username, question, rubricPanes):
#     try:
#         paneConfigFilename = os.path.join(
#             "userRubricPaneData", "rubricPanes.{}.{}.json".format(username, question)
#         )
#         with open(paneConfigFilename, "w") as outfile:
#             json.dump(rubricPanes, outfile)
#         return True
#     except:
#         return False
