# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2022 Colin B. Macdonald

"""
Solution-related server methods.
"""

import logging
import os
import hashlib

log = logging.getLogger("server")


def getSolutionStatus(self):
    status = []
    for q in range(1, self.testSpec["numberOfQuestions"] + 1):
        if self.testSpec["question"][str(q)]["select"] == "shuffle":
            vm = self.testSpec["numberOfVersions"]
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
                    status.append([q, v, hashlib.md5(img_obj).hexdigest()])
            else:  # else return empty string
                status.append([q, v, ""])
    return status


def getSolutionImage(self, question, version):
    solutionFile = os.path.join(
        "solutionImages", "solution.{}.{}.png".format(question, version)
    )
    if os.path.isfile(solutionFile):
        return solutionFile
    else:
        return None


def deleteSolutionImage(self, question, version):
    solutionFile = os.path.join(
        "solutionImages", "solution.{}.{}.png".format(question, version)
    )
    if os.path.isfile(solutionFile):
        os.remove(solutionFile)
        return True
    else:
        return False


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
