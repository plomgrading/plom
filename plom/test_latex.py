# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2025 Colin B. Macdonald

import tempfile
from importlib import resources

import plom

from .textools import buildLaTeX


def test_latex_exam_template() -> None:
    content = (resources.files(plom) / "latexTemplate.tex").read_text()
    with tempfile.NamedTemporaryFile() as f:
        r, out = buildLaTeX(content, f)
        assert r == 0


def test_latex_exam_templatev2() -> None:
    content = (resources.files(plom) / "latexTemplatev2.tex").read_text()
    with tempfile.NamedTemporaryFile() as f:
        r, out = buildLaTeX(content, f)
        assert r == 0


def test_latex_fails_and_makes_useful_output() -> None:
    content = r"""\documentclass{article}
        \begin{document}
        \InvalidCommand
        \end{document}
    """
    with tempfile.NamedTemporaryFile() as f:
        r, out = buildLaTeX(content, f)
        assert r != 0
        assert r"\InvalidCommand" in out
        assert "Undefined" in out
