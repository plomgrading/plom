import os
from .demotools import buildDemoSourceFiles


def test_latex_demofiles(tmp_path):
    cdir = os.getcwd()
    os.chdir(tmp_path)
    assert buildDemoSourceFiles()
    assert set(os.listdir("sourceVersions")) == set(("version1.pdf", "version2.pdf"))
    os.chdir(cdir)
