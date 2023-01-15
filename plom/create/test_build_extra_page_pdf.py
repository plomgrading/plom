# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Colin B. Macdonald
# Copyright (C) 2020 Dryden Wiebe

import os

from pathlib import Path
from .build_extra_page_with_qrcodes import build_extra_page_pdf
from ..misc_utils import working_directory


def test_latex_demofiles(tmpdir):
    """Builds the demo LaTeX source files and confirms the setup worked.

    Arguments:
        tmpdir (dir): The directory that we are building the files in.
    """
    with working_directory(tmpdir):
        ptp = Path("papersToPrint").absolute()
        ptp.mkdir()
        build_extra_page_pdf(destination_dir=ptp)
        assert set(os.listdir(ptp)) == set(["extra_page.pdf"])
