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

import fitz
import pandas

from . import paperdir as _paperdir


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
    "Now 0 = 0 so therefore 5 = 1."
    "I mean, you could claim that anything's real if the only basis for "
    "believing in it is that nobody's proved it doesn't exist!  -- Hermione Granger",
]


def fillInExams(paperdir, classlist, outfile, which=None):
    """Simulate writing an exam by scribbling names, numbers, and answers.

    Args:
        paperdir: directory containing the blank exams.
            Can be a string or anything convertable to pathlib `Path` object.
        classlist: path and filename of the classlist (as csv file).
        outfile: write results into this concatenated PDF file.
        which (optional): by default, scribble on all exams or specify
            something like `which=range(10, 16)` here to scribble on a
            subset.
    """
    paperdir = Path(paperdir)
    classlist = Path(classlist)
    outfile = Path(outfile)

    if not which:
        papers = glob(str(paperdir / "exam_*.pdf"))
    else:
        papers = [paperdir / "exam_{}.pdf".format(str(i).zfill(4)) for i in which]

    df = pandas.read_csv(classlist, dtype="object")
    # sample from the classlist
    df = df.sample(len(papers))

    bigdoc = fitz.open()

    blue = [0, 0, 0.75]

    for i, fname in enumerate(papers):
        r = df.iloc[i]
        print((fname, r.id, r.studentName))

        name = r.studentName
        sn = str(r.id)

        doc = fitz.open(fname)
        page = doc[0]

        # TODO: use insertText
        rect1 = fitz.Rect(228, 262, 550, 350)
        rect2 = fitz.Rect(228, 335, 550, 450)

        # manually kern the student number to fit the boxes
        text = "   ".join([c for c in sn])

        rc = page.insertTextbox(
            rect1,
            text,
            fontsize=25.5,
            color=blue,
            fontname="Helvetica",
            fontfile=None,
            align=0,
        )
        assert rc > 0

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


if __name__ == "__main__":
    specdir = Path("specAndDatabase")
    classlist = specdir / "classlist.csv"
    outfile = "fake_scribbled_exams.pdf"
    fillInExams(_paperdir, classlist, outfile)
