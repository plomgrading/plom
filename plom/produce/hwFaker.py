# -*- coding: utf-8 -*-

"""Plom tools for scribbling fake answers on PDF files"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import argparse
import csv
import os
import random
from pathlib import Path
from glob import glob

import json
import base64
import fitz

from . import paperdir as _paperdir
from plom import specdir as _specdir
from plom import specParser
from plom import __version__


possibleAns = [
    "I am so sorry, I really did study this... :(",
    "I know this, I just can't explain it",
    "Hey, at least its not in Comic Sans",
    "Life moves pretty fast. If you don't stop and look around once in a while, "
    "you could miss it.  -- Ferris Bueler",
    "Stupid is as stupid does.  -- Forrest Gump",
    "Of course, it is very important to be sober when you take an exam.  "
    "Many worthwhile careers in the street-cleansing, fruit-picking and "
    "subway-guitar-playing industries have been founded on a lack of "
    "understanding of this simple fact.  -- Terry Pratchett",
    "The fundamental cause of the trouble in the modern world today is that "
    "the stupid are cocksure while the intelligent are full of doubt.  "
    "-- Bertrand Russell",
    "Numbers is hardly real and they never have feelings\n"
    "But you push too hard, even numbers got limits.  -- Mos Def",
    "I was doin' 150 miles an hour sideways\n"
    "And 500 feet down at the same time\n"
    "I was lookin' for the cops, 'cuz you know\n"
    "I knew that it, it was illegal  -- Arlo Guthrie",
    "But there will always be science, engineering, and technology.  "
    "And there will always, always be mathematics.  -- Katherine Johnson",
    "Is 5 = 1?  Let's see... multiply both sides by 0.  "
    "Now 0 = 0 so therefore 5 = 1.",
    "I mean, you could claim that anything's real if the only basis for "
    "believing in it is that nobody's proved it doesn't exist!  -- Hermione Granger",
]


def makeFakeHW(numberOfQuestions, paperNumber, studentID, studentName):
    # with open("digits.json", "rb") as digitData:
    # digitArray = json.load(digitData)
    did = random.randint(
        numberOfQuestions - 1, numberOfQuestions
    )  # some subset of questions.
    doneQ = random.sample(list(range(1, 1 + numberOfQuestions)), did)
    for q in doneQ:
        fname = Path("submittedHomework") / "hw.{}.{}.pdf".format(studentID, q)
        doc = fitz.open()
        # construct pages
        for pn in range(random.randint(1, 3)):
            page = doc.newPage(0, 612, 792)
            rect = fitz.Rect(
                100 + 30 * random.random(), 150 + 20 * random.random(), 500, 500
            )
            text = random.choice(possibleAns)
            rc = page.insertTextbox(
                rect,
                text,
                fontsize=13,
                color=[0.1, 0.1, 0.8],
                fontname="helv",
                fontfile=None,
                align=0,
            )
            assert rc > 0

        # put name and student number on p1 of the submission
        page = doc[0]
        rect1 = fitz.Rect(20, 24, 300, 44)
        rc = page.insertTextbox(
            rect1,
            "Q.{} -".format(q) + studentName + ":" + studentID,
            fontsize=12,
            color=[0.1, 0.1, 0.1],
            fontname="helv",
            fontfile=None,
            align=0,
        )
        assert rc > 0

        doc.save(fname)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    args = parser.parse_args()

    os.makedirs("submittedHomework", exist_ok=True)

    # some cludgery here for the moment

    # grab classlist
    specdir = Path(_specdir)
    classlist = specdir / "classlist.csv"
    # read in the spec
    spec = specParser.SpecParser()
    # get number named
    numberNamed = spec.spec["numberToName"]
    numberOfQuestions = spec.spec["numberOfQuestions"]
    # the named papers come from the first few lines of classlist
    sid = {}
    with open(classlist, "r") as fh:
        clr = csv.reader(fh)
        next(clr)  # skip the header
        k = 0
        for row in clr:
            sid[k] = [row[0], row[1]]
            k += 1
            if k >= numberNamed:
                break

    for k in range(numberNamed):
        makeFakeHW(numberOfQuestions, k, sid[k][0], sid[k][1])


if __name__ == "__main__":
    main()
