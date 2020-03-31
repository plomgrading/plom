# -*- coding: utf-8 -*-

"""Tools for working with TeX"""

__copyright__ = "Copyright (C) 2018-2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

import pkg_resources


def texFragmentToPNG(fragment, outName):
    """Process a fragment of latex and produce a png image."""

    head = r"""
    \documentclass[12pt]{article}
    \usepackage[letterpaper, textwidth=5in]{geometry}
    \usepackage{amsmath, amsfonts}
    \usepackage{xcolor}
    \usepackage[active, tightpage]{preview}
    \begin{document}
    \begin{preview}
    \color{red}
    """

    foot = r"""
    \end{preview}
    \end{document}
    """

    # make a temp dir to build latex in
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "frag.tex"), "w") as fh:
            fh.write(head)
            fh.write(fragment)
            fh.write(foot)

        latexIt = subprocess.run(
            [
                "latexmk",
                "-quiet",
                "-interaction=nonstopmode",
                "-no-shell-escape",
                "frag.tex",
            ],
            cwd=tmpdir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if latexIt.returncode != 0:
            return False

        convertIt = subprocess.run(
            [
                "dvipng",
                "-q",
                "-D",
                "225",
                "-bg",
                "transparent",
                "frag.dvi",
                "-o",
                "frag.png",
            ],
            cwd=tmpdir,
            stdout=subprocess.DEVNULL,
        )
        if convertIt.returncode != 0:
            # sys.exit(convertIt.returncode)
            return False

        shutil.copyfile(os.path.join(tmpdir, "frag.png"), outName)
    return True


def buildLaTeX(src, out):
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
