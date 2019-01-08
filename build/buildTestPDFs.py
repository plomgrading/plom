__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018 Andrew Rechnitzer"
__license__ = "GPLv3"

import json
import os
import sys

# the following allows us to import from ../resources
sys.path.append("..")
from resources.testspecification import TestSpecification


def readExams():
    """Read the list of exams produced from datafile"""
    global exams
    with open("../resources/examsProduced.json") as data_file:
        exams = json.load(data_file)


def scriptBuild():
    """Rerun mergeandcode script to rebuild all the exams
    Build a list of commands and pipe through gnu-parallel
    to take advantage of multiple processors
    """
    fh = open("./commandlist.txt", "w")
    for x in exams:
        fh.write(
            'python3 mergeAndCodePages.py {} {} {} {} "{}"\n'.format(
                spec.Name, spec.Length, spec.Versions, x, exams[x]
            )
        )
    fh.close()
    os.system("parallel --bar <commandlist.txt")


spec = TestSpecification()
spec.readSpec()
exams = {}
readExams()
scriptBuild()
