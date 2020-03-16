import tempfile
from pytest import raises

from plom.server.latex2png import processFragment
# TODO: this too: pageNotSubmitted

f = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name

def test_frag_latex():
    frag = r"\( \mathbb{Z} / \mathbb{Q} \) The cat sat on the mat and verified \LaTeX\ works for Plom."
    assert processFragment(frag, f)


def test_frag_broken_tex():
    frag = r"``Not that dinner.  The Right Dinner'' \saidTheCat"
    assert not processFragment(frag, f)


#TODO: plus an imagemagick compare test that it produces what is expected
