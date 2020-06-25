import tempfile
import subprocess
import pkg_resources
from PIL import Image
from io import BytesIO
from pytest import raises

from .textools import texFragmentToPNG as processFragment

# TODO: this too: pageNotSubmitted


def relativeErr(x, y):
    return float(abs(x - y)) / float(abs(x))


f = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name


def test_frag_latex():
    frag = r"\( \mathbb{Z} / \mathbb{Q} \) The cat sat on the mat and verified \LaTeX\ works for Plom."
    assert processFragment(frag, f)


def test_frag_broken_tex():
    frag = r"``Not that dinner.  The Right Dinner'' \saidTheCat"
    assert not processFragment(frag, f)


def test_frag_image_size():
    imgt = Image.open(
        BytesIO(pkg_resources.resource_string("plom.server", "target_Q_latex_plom.png"))
    )

    frag = r"$\mathbb{Q}$ \LaTeX\ Plom"
    assert processFragment(frag, f)
    img = Image.open(f)
    # no more than 5% error in width/height
    assert relativeErr(img.width, imgt.width) < 0.05
    assert relativeErr(img.height, imgt.height) < 0.05

    frag = r"$z = \frac{x + 3}{y}$ and lots and lots more, so its much longer."
    assert processFragment(frag, f)
    img = Image.open(f)
    assert img.width > 2 * imgt.width


def test_frag_image():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as target:
        with open(target.name, "wb") as fh:
            fh.write(
                pkg_resources.resource_string("plom.server", "target_Q_latex_plom.png")
            )

        frag = r"$\mathbb{Q}$ \LaTeX\ Plom"
        assert processFragment(frag, f)
        r = subprocess.run(
            ["compare", "-metric", "AE", f, target.name, "null"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        # Note "AE" not "rmse" with transparency www.imagemagick.org/Usage/compare/
        s = r.stderr.decode()
        assert float(s) < 3000
