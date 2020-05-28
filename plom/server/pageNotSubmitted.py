#!/usr/bin/env python3

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer"
__license__ = "AGPLv3"

import fitz
import json
import os
import shutil
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from plom import specdir
from plom.textools import buildLaTeX

def build_substitute(test, page, ver):
    """If all is good then build a substitute page and save it in the correct place.

    Arguments:
        test {int} -- The test number.
        page {int} -- The page number.
        ver {int} -- Version number

    Returns:
        bool -- True if successful.
    """
    tpImage = tempfile.NamedTemporaryFile(suffix=".png", delete=False)

    DNS = fitz.open(Path(specdir) / "pageNotSubmitted.pdf")

    # create a box for the test number near top-centre
    # Get page width
    page_width = DNS[0].bound().width
    rect = fitz.Rect(page_width // 2 - 40, 20, page_width // 2 + 40, 44)
    text = "{}.{}".format(str(test).zfill(4), str(page).zfill(2))
    rc = DNS[0].insertTextbox(
        rect,
        text,
        fontsize=18,
        color=[0, 0, 0],
        fontname="Helvetica",
        fontfile=None,
        align=1,
    )
    DNS[0].drawRect(rect, color=[0, 0, 0])

    scale = 200 / 72
    img = DNS[0].getPixmap(alpha=False, matrix=fitz.Matrix(scale, scale))
    img.writePNG("pns.{}.{}.{}.png".format(test, page, ver))
    DNS.close()
    return True


# If all is good then build a substitute question and save it in the correct place
def buildHWQuestionSubstitute(sid, question):
    hwqImage = tempfile.NamedTemporaryFile(suffix=".png", delete=False)

    DNS = fitz.open(Path(specdir) / "questionNotSubmitted.pdf")

    # create a box for the test number near top-centre
    # Get page width
    pW = DNS[0].bound().width
    rect = fitz.Rect(pW // 2 - 40, 20, pW // 2 + 40, 44)
    text = "{}.{}".format(sid, question)
    rc = DNS[0].insertTextbox(
        rect,
        text,
        fontsize=18,
        color=[0, 0, 0],
        fontname="Helvetica",
        fontfile=None,
        align=1,
    )
    DNS[0].drawRect(rect, color=[0, 0, 0])

    scale = 200 / 72
    img = DNS[0].getPixmap(alpha=False, matrix=fitz.Matrix(scale, scale))
    img.writePNG("qns.{}.{}.png".format(sid, question))
    DNS.close()
    return True


def buildPNSPage(outName):
    PNStex = r"""
\documentclass[12pt,letterpaper]{article}
\usepackage[]{fullpage}
\usepackage{xcolor}
\usepackage[printwatermark]{xwatermark}
\newwatermark[allpages,color=red!30,angle=-45,scale=2]{Page not submitted}
\pagestyle{empty}
\begin{document}
\emph{This page of the test was not submitted.}
\vfill
\emph{This page of the test was not submitted.}
\end{document}
"""
    with open(outName, "wb") as f:
        returncode, _ = buildLaTeX(PNStex, f)
    if returncode != 0:
        print(">>> Latex problems - see below <<<\n")
        print(out)
        print(">>> Latex problems - see above <<<")
        return False
    return True


def buildQNSPage(outName):
    PNStex = r"""
\documentclass[12pt,letterpaper]{article}
\usepackage[]{fullpage}
\usepackage{xcolor}
\usepackage[printwatermark]{xwatermark}
\newwatermark[allpages,color=red!30,angle=-45,scale=2]{Question not submitted}
\pagestyle{empty}
\begin{document}
\emph{This question was not submitted.}
\vfill
\emph{This question was not submitted.}
\end{document}
"""
    with open(outName, "wb") as f:
        returncode, out = buildLaTeX(PNStex, f)
    if returncode != 0:
        print(">>> Latex problems - see below <<<\n")
        print(out)
        print(">>> Latex problems - see above <<<")
        return False
    return True
