#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2024 Colin B. Macdonald

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import segno

import plom.create
from plom.tpv_utils import encodeScrapPaperCode

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources


def build_scrap_paper_pdf(destination_dir=None) -> None:
    if destination_dir is None:
        destination_dir = Path.cwd()

    src_tex = (resources.files(plom.create) / "scrap_paper_src.tex").read_text()
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path = Path(tmpdirname)
        with open(tmp_path / "scrap_paper.tex", "w") as fh:
            fh.write(src_tex)

        for crn in range(1, 9):
            qr = segno.make_micro(encodeScrapPaperCode(crn))
            # MyPy complains about pathlib.Path here but it works
            qr.save(tmp_path / f"qr_crn_{crn}.png", border=2, scale=4)  # type: ignore[arg-type]

        subprocess.run(
            (
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-no-shell-escape",
                "scrap_paper",
            ),
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
        )
        shutil.copy(tmp_path / "scrap_paper.pdf", destination_dir)


if __name__ == "__main__":
    build_scrap_paper_pdf()
