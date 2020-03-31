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
    if not buildLaTeXExam2(content, Path("sourceVersions") / "version1.pdf"):
        return False

    print("LaTeXing example exam file: latexTemplatev2.tex")
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
        r, out = buildLaTeXExam(src, f)
    if r:
        print(">>> Latex problems - see below <<<\n")
        print(out)
        print(">>> Latex problems - see above <<<")
        return False
    return True


def buildLaTeXExam(src, out):
    """Compile a string or bytes of latex.

    Args:
        src (str, bytes):
        out (file-like):

    Returns:
        exit value from the subprocess call (zero good, non-zero BAD)
        stdout/stderr from the subprocess call

    TODO: this is more generally useful but how to handle the idBox2?
    """

    with tempfile.TemporaryDirectory() as tmpdir:

        tmp = pkg_resources.resource_string("plom", "testTemplates/idBox2.pdf")
        with open(Path(tmpdir) / "idBox2.pdf", "wb") as fh:
            fh.write(tmp)

        # TODO: this is not very duck-type of us!
        if isinstance(src, bytes):
            mode = "wb"
        else:
            mode = "w"

        with open(Path(tmpdir) / "stuff.tex", mode) as fh:
            fh.write(src)

        latexIt = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-no-shell-escape",
                "stuff.tex",
            ],
            cwd=tmpdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        if latexIt.returncode == 0:
            out.write((Path(tmpdir) / "stuff.pdf").read_bytes())

    return latexIt.returncode, latexIt.stdout.decode()


if __name__ == "__main__":
    if not buildDemoSourceFiles():
        exit(1)
