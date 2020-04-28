# -*- coding: utf-8 -*-

"""Plom tools for scribbling fake answers on PDF files"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys
import subprocess
import random
from pathlib import Path
from glob import glob

import json
import base64
import fitz
import pandas

# import tools for dealing with resource files
import pkg_resources

from . import paperdir as _paperdir
from plom import specdir as _specdir


# load the digit images
digitArray = json.load(pkg_resources.resource_stream("plom", "produce/digits.json"))
# how many of each digit were collected
NDigit = len(digitArray) // 10
assert len(digitArray) % 10 == 0


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


def fillInFakeDataOnExams(paperdir, classlist, outfile, which=None):
    """Simulate writing an exam by scribbling names, numbers, and answers.

    Args:
        paperdir: directory containing the blank exams.
            Can be a string or anything convertible to pathlib `Path` object.
        classlist: path and filename of the classlist (as csv file).
        outfile: write results into this concatenated PDF file.
        which (optional): by default, scribble on all exams or specify
            something like `which=range(10, 16)` here to scribble on a
            subset.
    """

    paperdir = Path(paperdir)
    classlist = Path(classlist)
    outfile = Path(outfile)

    print("Annotating papers with fake student data and scribbling on pages...")
    if not which:
        namedPapers = glob(str(paperdir / "exam_*_*.pdf"))  # those with an ID number
        papers = glob(str(paperdir / "exam_*.pdf"))  # everything
    else:
        papers = [paperdir / "exam_{}.pdf".format(str(i).zfill(4)) for i in which]

    df = pandas.read_csv(classlist, dtype="object")
    # sample from the classlist
    df = df.sample(len(papers))

    bigdoc = fitz.open()

    blue = [0, 0, 0.75]

    for i, fname in enumerate(papers):
        r = df.iloc[i]
        print(
            "  {}: {}, {}, scribbled".format(
                os.path.basename(fname), r.id, r.studentName
            )
        )

        if fname not in namedPapers:  # can draw on front page
            name = r.studentName
            sn = str(r.id)

            doc = fitz.open(fname)
            page = doc[0]

            # insert digit images into rectangles - some hackery required to get correct positions.
            w = 28
            b = 8
            for k in range(8):
                rect1 = fitz.Rect(
                    220 + b * k + w * k, 265, 220 + b * k + w * (k + 1), 265 + w
                )
                uuImg = digitArray[
                    int(sn[k]) * NDigit + random.randrange(NDigit)
                ]  # uu-encoded png
                imgBString = base64.b64decode(uuImg)
                page.insertImage(rect1, stream=imgBString, keep_proportion=True)
                # todo - there should be an assert or something here?

            rect2 = fitz.Rect(228, 335, 550, 450)
            rc = page.insertTextbox(
                rect2,
                name,
                fontsize=24,
                color=blue,
                fontname="Helvetica",
                fontfile=None,
                align=0,
            )
            assert rc > 0

        # write some stuff on pages
        for j, pg in enumerate(doc):
            rect = fitz.Rect(
                100 + 30 * random.random(), 150 + 20 * random.random(), 500, 500
            )
            text = random.choice(possibleAns)

            # TODO: "helv" vs "Helvetica"
            if j >= 1:
                rc = pg.insertTextbox(
                    rect,
                    text,
                    fontsize=13,
                    color=blue,
                    fontname="helv",
                    fontfile=None,
                    align=0,
                )
                assert rc > 0

        # doc.saveIncr()   # update file
        # doc.save("new{}.pdf".format(str(which[i]).zfill(4)))
        bigdoc.insertPDF(doc)
        doc.close()

    # need to use `str(outfile)` for pumypdf < 1.16.14
    # https://github.com/pymupdf/PyMuPDF/issues/466
    bigdoc.save(outfile)
    print('Assembled in "{}"'.format(outfile))


def main():
    specdir = Path(_specdir)
    classlist = specdir / "classlist.csv"
    outfile = "fake_scribbled_exams.pdf"
    fillInFakeDataOnExams(_paperdir, classlist, outfile)


if __name__ == "__main__":
    main()
