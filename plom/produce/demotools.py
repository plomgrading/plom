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
    td = tempfile.TemporaryDirectory()

    tmp = pkg_resources.resource_string("plom", "testTemplates/idBox2.pdf")
    with open(Path(td.name) / "idBox2.pdf.tex", "wb") as fh:
        fh.write(tmp)

    template = pkg_resources.resource_string("plom", "testTemplates/latexTemplate.tex")
    with open(Path(td.name) / "version1.tex", "wb") as fh:
        fh.write(template)
    template = pkg_resources.resource_string("plom", "testTemplates/latexTemplatev2.tex")
    with open(Path(td.name) / "version2.tex", "wb") as fh:
        fh.write(template)

    cdir = os.getcwd()
    os.chdir(td.name)

    for x in ("version1", "version2"):
        latexIt = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-quiet",
                "-interaction=nonstopmode",
                "-no-shell-escape",
                x,
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
    for x in ("version1.pdf", "version2.pdf"):
        shutil.copyfile(Path(td.name) / x, Path("sourceVersions") / x)
    return True


if __name__ == "__main__":
    print("LaTeXing example exam files")
    if not buildDemoSourceFiles():
        exit(1)
