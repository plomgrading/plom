#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import segno

import plom.create
from plom.tpv_utils import encodeBundleSeparatorPaperCode

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources


def build_bundle_separator_paper_pdf(
    destination_dir=None, *, latex_papersize: str = ""
) -> Path:
    """Build the bundle separator pdf file.

    Similar to :func:`build_extra_page_pdf`.
    """
    if destination_dir is None:
        destination_dir = Path.cwd()
    src_tex = (resources.files(plom.create) / "bundle_separator_src.tex").read_text()
    if latex_papersize:
        src_tex = src_tex.replace("letterpaper", latex_papersize)
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path = Path(tmpdirname)
        with open(tmp_path / "bundle_separator_paper.tex", "w") as fh:
            fh.write(src_tex)

        for crn in range(1, 9):
            qr = segno.make_micro(encodeBundleSeparatorPaperCode(crn))
            # MyPy complains about pathlib.Path here but it works
            qr.save(tmp_path / f"qr_crn_{crn}.png", border=2, scale=4)  # type: ignore[arg-type]

        subprocess.run(
            (
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-no-shell-escape",
                "bundle_separator_paper",
            ),
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
        )
        shutil.copy(tmp_path / "bundle_separator_paper.pdf", destination_dir)
    return Path(destination_dir) / "bundle_separator_paper.pdf"


if __name__ == "__main__":
    build_bundle_separator_paper_pdf()
