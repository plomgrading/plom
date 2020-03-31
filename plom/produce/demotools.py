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
    """Take a string or bytes and compile it.

    Generally silent and returns True if everything worked.  If it
    returns False, it should print errors messages to stdout.
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
        if latexIt.returncode != 0:
            # sys.exit(latexIt.returncode)
            print(">>> Latex problems - see below <<<\n")
            print(latexIt.stdout.decode())
            print(">>> Latex problems - see above <<<")
            os.chdir(cdir)
            return False
    os.chdir(cdir)

    os.makedirs("sourceVersions", exist_ok=True)
    shutil.copyfile(Path(td.name) / "stuff.pdf", name)
    return True


if __name__ == "__main__":
    if not buildDemoSourceFiles():
        exit(1)
