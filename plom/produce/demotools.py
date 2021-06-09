# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

"""Build pdf files for a demo test and provide demo classlists"""

__copyright__ = "Copyright (C) 2020-2021 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import os
from pathlib import Path
import sys

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import pandas

import plom
from plom.textools import buildLaTeX


def getDemoClassList():
    """A classlist for demos.

    returns:
        pandas.dataframe: the classlist as a Pandas dataframe.
    """
    with resources.open_binary(plom, "demoClassList.csv") as f:
        return pandas.read_csv(f)


def getDemoClassListLength():
    """How long is the built-in demo classlist."""
    return getDemoClassList().shape[0]


def buildDemoSourceFiles():
    """Builds the LaTeX source files for the demo.

    Returns:
        bool: True if successful, False if it failed.
    """
    os.makedirs("sourceVersions", exist_ok=True)
    print("LaTeXing example exam file: latexTemplate.tex -> version1.pdf")
    content = resources.read_text(plom, "latexTemplate.tex")
    if not buildLaTeXExam2(content, Path("sourceVersions") / "version1.pdf"):
        return False

    print("LaTeXing example exam file: latexTemplatev2.tex -> version2.pdf")
    content = resources.read_text(plom, "latexTemplatev2.tex")
    if not buildLaTeXExam2(content, Path("sourceVersions") / "version2.pdf"):
        return False
    return True


def buildLaTeXExam2(src, filename):
    """Compile a string of latex to PDF.

    Arguments:
        src (str): LaTeX source to build.
        filename (str): The name of the file.

    Returns:
        bool: True if everything worked.  Print to stdout and return
            False if latex failed.
    """

    with open(filename, "wb") as f:
        r, out = buildLaTeX(src, f)
    if r:
        print(">>> Latex problems - see below <<<\n")
        print(out)
        print(">>> Latex problems - see above <<<")
        return False
    return True


def main():
    if not buildDemoSourceFiles():
        exit(1)


if __name__ == "__main__":
    main()
