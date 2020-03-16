import tempfile
import subprocess
import pkg_resources
from pytest import raises

from plom.server.latex2png import processFragment

# TODO: this too: pageNotSubmitted

f = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name


def test_frag_latex():
    frag = r"\( \mathbb{Z} / \mathbb{Q} \) The cat sat on the mat and verified \LaTeX\ works for Plom."
    assert processFragment(frag, f)


def test_frag_broken_tex():
    frag = r"``Not that dinner.  The Right Dinner'' \saidTheCat"
    assert not processFragment(frag, f)


def test_frag_image_as_expected():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as target:
        with open(target.name, "wb") as fh:
            fh.write(pkg_resources.resource_string("plom.server", "target_Q_latex_plom.png"))

        frag = r"$\mathbb{Q}$ \LaTeX\ Plom"
        assert processFragment(frag, f)
        r = subprocess.run(
            ["compare", "-metric", "rmse", f, target.name, "-"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        # output is "float (float)"
        s = r.stderr.decode().split(" ")[1].strip("()")
        assert float(s) < 0.2

        frag = r"$f = \frac{x}{y}$ and lots and lots more, very different."
        assert processFragment(frag, f)
        r = subprocess.run(
            ["compare", "-metric", "rmse", f, target.name, "-"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        # output is "float (float)"
        s = r.stderr.decode().split(" ")[1].strip("()")
        assert float(s) > 0.25
