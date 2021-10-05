# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import os
from pathlib import Path

from .demotools import buildDemoSourceFiles
from ..misc_utils import working_directory


def test_latex_demofiles(tmpdir):
    """Builds the demo LaTeX source files and confirms the setup worked.

    Arguments:
        tmpdir (dir): The directory that we are building the files in.
    """
    with working_directory(tmpdir):
        assert buildDemoSourceFiles()
        assert set(os.listdir("sourceVersions")) == set(
            ("version1.pdf", "version2.pdf")
        )


def test_latex_demofiles_dir(tmpdir):
    tmp = Path(tmpdir)
    assert buildDemoSourceFiles(tmp)
    pdfs = [x.name for x in (tmp / "sourceVersions").glob("*.pdf")]
    assert set(pdfs) == set(("version1.pdf", "version2.pdf"))
