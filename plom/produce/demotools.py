# -*- coding: utf-8 -*-

"""Build pdf files for a demo test"""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path

import pkg_resources


def buildDemoSourceFiles():
    os.makedirs("sourceVersions", exist_ok=True)
    print("LaTeXing example exam file: latexTemplate.tex")
    content = pkg_resources.resource_string("plom", "testTemplates/latexTemplate.tex")
    if not buildLaTeXExam(content, Path("sourceVersions") / "version1.pdf"):
        return False

    print("LaTeXing example exam file: latexTemplatev2.tex")
    content = pkg_resources.resource_string("plom", "testTemplates/latexTemplatev2.tex")
    if not buildLaTeXExam(content, Path("sourceVersions") / "version2.pdf"):
        return False
    return True


def buildLaTeXExam(src, name):
    """Compile a string or bytes of latex.

    Generally silent and returns True if everything worked.  If it
    returns False, it should print errors messages to stdout.
    """
    r, out = buildLaTeXExam_raw(src, name)
    if r:
        print(">>> Latex problems - see below <<<\n")
        print(out)
        print(">>> Latex problems - see above <<<")
        return False
    return True


def buildLaTeXExam_raw(src, name):
    """Compile a string or bytes of latex.

    Returns:
        exit value from the subprocess call (zero good, non-zero BAD)
        stdout/stderr from the subprocess call
    """

    td = tempfile.TemporaryDirectory()

    tmp = pkg_resources.resource_string("plom", "testTemplates/idBox2.pdf")
    with open(Path(td.name) / "idBox2.pdf.tex", "wb") as fh:
        fh.write(tmp)

    with open(Path(td.name) / "stuff.tex", "wb") as fh:
        fh.write(src)

    # TODO: get context thingy
    cdir = os.getcwd()
    os.chdir(td.name)

    if True:
        latexIt = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-no-shell-escape",
                "stuff.tex",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    os.chdir(cdir)

    if latexIt.returncode == 0:
        shutil.copyfile(Path(td.name) / "stuff.pdf", name)

    return latexIt.returncode, latexIt.stdout.decode()


if __name__ == "__main__":
    if not buildDemoSourceFiles():
        exit(1)
