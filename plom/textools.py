# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2021 Colin B. Macdonald

"""Tools for working with TeX"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
import sys

if sys.version_info >= (3, 7):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import plom


def texFragmentToPNG(fragment, outName, dpi=225):
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
                str(dpi),
                "-bg",
                "Transparent",
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
    """Compile a string of latex.

    Args:
        src (str):
        out (file-like): the binary pdf file will be written into this.

    Returns:
        exit value from the subprocess call (zero good, non-zero BAD)
        stdout/stderr from the subprocess call

    TODO: this is more generally useful but how to handle the idBox2?
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(Path(tmpdir) / "idBox2.pdf", "wb") as fh:
            fh.write(resources.read_binary(plom, "idBox2.pdf"))
        with open(Path(tmpdir) / "stuff.tex", "w") as fh:
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
