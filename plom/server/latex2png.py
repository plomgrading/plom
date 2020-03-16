__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPLv3"

import os
import sys
import subprocess
import tempfile
import shutil


def processFragment(fragment, outName):
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
