# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2019-2023 Colin B. Macdonald
# Copyright (C) 2021 Forest Kobayashi

"""Tools for working with TeX"""

from pathlib import Path
import subprocess
import sys
import tempfile
from textwrap import dedent

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources

import plom


def texFragmentToPNG(fragment, *, dpi=225):
    """Process a fragment of latex and produce a png image.

    Args:
        fragment (str): a string of text to be rendered with LaTeX.
        dpi (int): controls the resolution of the image by setting
            the dots-per-inch.  Defaults: 225.

    Return:
        tuple: `(True, imgdata)` or `(False, error_msg)` where `imgdata`
        is the raw contents of a PNG file, and `error_msg` is
        (currently) a string, but this could change in the future.
    """

    head = dedent(
        r"""
        \documentclass[12pt]{article}
        \usepackage[letterpaper, textwidth=5in]{geometry}
        \usepackage{amsmath, amsfonts}
        \usepackage{xcolor}
        \usepackage[active]{preview}
        \begin{document}
        \begin{preview}
        \color{red}
        %
        """
    ).lstrip()

    foot = dedent(
        r"""
        %
        \end{preview}
        \end{document}
        """
    ).lstrip()

    tex = head + fragment + "\n" + foot

    # make a temp dir to build latex in
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(Path(tmpdir) / "frag.tex", "w") as fh:
            fh.write(tex)

        latexIt = subprocess.run(
            [
                "latexmk",
                "-interaction=nonstopmode",
                "-no-shell-escape",
                "-pdf-",
                "-ps-",
                "-dvi",
                "frag.tex",
            ],
            cwd=tmpdir,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )
        if latexIt.returncode != 0:
            errstr = "Code to compile\n"
            errstr += "---------------\n\n"
            errstr += tex
            errstr += "\n\nOutput from latexmk\n"
            errstr += "-------------------\n\n"
            errstr += latexIt.stdout.decode()
            return (False, errstr)

        convertIt = subprocess.run(
            [
                "dvipng",
                "--width",
                "--picky",
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
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )

        # dvipng will fail with e.g., pstricks: workaround is ps then use gs/convert.
        # To enable all this, we need a MWE, a unit test (that takes this code path).
        # Do we re-call latexmk with `-ps` and `-dvi-` or just do both above?
        #   - https://gitlab.com/plom/plom/-/issues/1523
        #   - https://trac.sagemath.org/ticket/6022
        #   - https://www.ghostscript.com/doc/9.54.0/Use.htm
        if False:
            convertIt = subprocess.run(
                [
                    "gs",
                    "-dSAFER",  # Give gs permission to modify filesystem
                    "-dBATCH",
                    "-dNOPAUSE",  # Skip prompting of user
                    "-sDEVICE=pngalpha",
                    f"-r{dpi}",
                    "-sOutputFile=frag.png",
                    "frag.ps",
                ],
                cwd=tmpdir,
                stderr=subprocess.STDOUT,
                stdout=subprocess.PIPE,
            )

        if convertIt.returncode != 0:
            errstr = "Code to compile\n"
            errstr += "---------------\n\n"
            errstr += tex
            errstr += "\n\nOutput from latexmk\n"
            errstr += "-------------------\n\n"
            errstr += latexIt.stdout.decode()
            errstr += "\n\nOutput from dvipng\n"
            errstr += "-------------------\n\n"
            errstr += convertIt.stdout.decode()
            return (False, errstr)

        with open(Path(tmpdir) / "frag.png", "rb") as f:
            return (True, f.read())


def buildLaTeX(src, out):
    """Compile a string of latex.

    Args:
        src (str):
        out (file-like): the binary pdf file will be written into this.

    Returns:
        tuple containing

        - (`int`): exit value from the subprocess call (zero good, non-zero bad)
        - (`str`): stdout/stderr from the subprocess call

    TODO: this is more generally useful but how to handle the idBox2?
    """

    with tempfile.TemporaryDirectory() as tmpdir:
        with open(Path(tmpdir) / "idBox2.pdf", "wb") as fh:
            fh.write((resources.files(plom) / "idBox2.pdf").read_bytes())
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
