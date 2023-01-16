#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from pathlib import Path
import segno
import shutil
import subprocess
import sys
import tempfile

import plom.create
from plom.misc_utils import working_directory
from plom.tpv_utils import encodeExtraPageCode

if sys.version_info >= (3, 9):
    import importlib.resources as resources
else:
    import importlib_resources as resources


def build_extra_page_pdf(destination_dir=Path.cwd()):
    print("Building the extra pages PDF for students to use when they need more space.")

    src_tex = (resources.files(plom.create) / "extra_pages_src.tex").read_text()
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path = Path(tmpdirname)
        with working_directory(tmp_path):
            with open("extra_page.tex", "w") as fh:
                fh.write(src_tex)

            for crn in range(1, 9):
                qr = segno.make_micro(encodeExtraPageCode(crn))
                qr.save(tmp_path / f"qr_crn_{crn}.png", border=2, scale=4)
            subprocess.run(
                (
                    "latexmk",
                    "-pdf",
                    "-interaction=nonstopmode",
                    "-no-shell-escape",
                    "extra_page",
                ),
                stdout=subprocess.DEVNULL,
            )
            shutil.copy("extra_page.pdf", destination_dir)
            print("Copying extra_page.pdf to ", Path(destination_dir).absolute())
