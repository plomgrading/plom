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

    cdir = os.getcwd()
    td = tempfile.TemporaryDirectory()
    os.chdir(td.name)

    with open(os.path.join(td.name, "frag.tex"), "w") as fh:
        fh.write(head)
        fh.write(fragment)
        fh.write(foot)

    latexIt = subprocess.run(
        ["latex", "-interaction=nonstopmode", "-no-shell-escape", "frag.tex"],
        stdout=subprocess.DEVNULL,
    )
    if latexIt.returncode != 0:
        # sys.exit(latexIt.returncode)
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
        stdout=subprocess.DEVNULL,
    )
    if convertIt.returncode != 0:
        # sys.exit(convertIt.returncode)
        return False

    shutil.copyfile("frag.png", outName)
    os.chdir(cdir)
    return True
