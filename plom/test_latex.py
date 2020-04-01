import tempfile

import pkg_resources

from .textools import buildLaTeX


def test_latex_exam_template():
    content = pkg_resources.resource_string("plom", "testTemplates/latexTemplate.tex")
    with tempfile.NamedTemporaryFile() as f:
        r, out = buildLaTeX(content, f)
        assert r == 0


def test_latex_exam_templatev2():
    content = pkg_resources.resource_string("plom", "testTemplates/latexTemplatev2.tex")
    with tempfile.NamedTemporaryFile() as f:
        r, out = buildLaTeX(content, f)
        assert r == 0


def test_latex_fails_and_makes_useful_output():
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
