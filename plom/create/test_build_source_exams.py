# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021, 2024 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import os

from .demotools import buildDemoSourceFiles
from ..misc_utils import working_directory


def test_latex_demofiles(tmp_path) -> None:
    """Builds the demo LaTeX source files and confirms the files exist."""
    with working_directory(tmp_path):
        assert buildDemoSourceFiles()
        assert set(os.listdir("sourceVersions")) == set(
            ("version1.pdf", "version2.pdf")
        )


def test_latex_demofiles_dir(tmp_path) -> None:
    assert buildDemoSourceFiles(tmp_path)
    pdfs = [x.name for x in (tmp_path / "sourceVersions").glob("*.pdf")]
    assert set(pdfs) == set(("version1.pdf", "version2.pdf"))
