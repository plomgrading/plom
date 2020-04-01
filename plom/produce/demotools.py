# -*- coding: utf-8 -*-

"""Build pdf files for a demo test"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
from pathlib import Path

import pkg_resources

from plom.textools import buildLaTeX


def buildDemoSourceFiles():
    os.makedirs("sourceVersions", exist_ok=True)
    print("LaTeXing example exam file: latexTemplate.tex -> version1.pdf")
    content = pkg_resources.resource_string("plom", "testTemplates/latexTemplate.tex")
    if not buildLaTeXExam2(content, Path("sourceVersions") / "version1.pdf"):
        return False

    print("LaTeXing example exam file: latexTemplatev2.tex -> version2.pdf")
    content = pkg_resources.resource_string("plom", "testTemplates/latexTemplatev2.tex")
    if not buildLaTeXExam2(content, Path("sourceVersions") / "version2.pdf"):
        return False
    return True


def buildLaTeXExam2(src, filename):
    """Compile a string or bytes of latex.

    Silent and return True if everything worked, print to stdout and
    return False if latex failed.
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
