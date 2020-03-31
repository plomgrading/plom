import os
from .demotools import buildDemoSourceFiles


def test_latex_demofiles(tmpdir):
    cdir = os.getcwd()
    os.chdir(tmpdir)
    assert buildDemoSourceFiles()
    assert set(os.listdir("sourceVersions")) == set(("version1.pdf", "version2.pdf"))
    os.chdir(cdir)
