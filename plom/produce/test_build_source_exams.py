import os
from .demotools import buildDemoSourceFiles


def test_latex_demofiles(tmpdir):
    """Builds the demo LaTeX source files and confirms the setup worked.

    Arguments:
        tmpdir {str} -- The directory that we are building the files in.
    """
    cdir = os.getcwd()
    os.chdir(tmpdir)
    assert buildDemoSourceFiles()
    assert set(os.listdir("sourceVersions")) == set(("version1.pdf", "version2.pdf"))
    os.chdir(cdir)
