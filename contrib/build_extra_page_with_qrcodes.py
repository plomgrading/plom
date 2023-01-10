#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path
from plom.misc_utils import working_directory
import segno
import shutil
import subprocess
import tempfile


base = "plomX"
src_tex_file = "build_extra_page_with_qrcodes_src.tex"
src_tex_path = Path(src_tex_file).absolute()
latexmk_exec = "latexmk"

current_dir = Path.cwd().absolute()

with tempfile.TemporaryDirectory() as tmpdirname:
    tmp_path = Path(tmpdirname)
    with working_directory(tmp_path):
        shutil.copy(src_tex_path, "extra_page.tex")
        for crn in range(1, 9):
            qr = segno.make_micro(f"{base}{crn}")
            qr.save(tmp_path / f"qr_crn_{crn}.eps", border=2)
        subprocess.run(
            (
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-no-shell-escape",
                "extra_page",
            )
        )
        shutil.copy("extra_page.pdf", current_dir)
