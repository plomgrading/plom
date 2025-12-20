#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023-2025 Colin B. Macdonald

import shutil
import subprocess
import tempfile
from importlib import resources
from pathlib import Path

import segno

import plom.create
from plom.tpv_utils import encodeExtraPageCode


def build_extra_page_pdf(destination_dir=None, *, papersize: str = "") -> None:
    """Build the extra page pdf file.

    Args:
        destination_dir: if specified, build here, else in the current
            working directory.

    Keyword Args:
        papersize: the latex-compatible papersize, e.g., "letterpaper"
            or "a4paper".  Defaults to file contents, current "letterpaper"
            if omitted.

    Returns:
        None, but places the file extra_pages.pdf in the specified directory.
    """
    if destination_dir is None:
        destination_dir = Path.cwd()

    src_tex = (resources.files(plom.create) / "extra_pages_src.tex").read_text()
    if papersize:
        src_tex = src_tex.replace("letterpaper", papersize)
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmp_path = Path(tmpdirname)
        with open(tmp_path / "extra_page.tex", "w") as fh:
            fh.write(src_tex)

        for crn in range(1, 9):
            qr = segno.make_micro(encodeExtraPageCode(crn))
            # MyPy complains about pathlib.Path here but it works
            qr.save(tmp_path / f"qr_crn_{crn}.png", border=2, scale=4)  # type: ignore[arg-type]

        subprocess.run(
            (
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-no-shell-escape",
                "extra_page",
            ),
            cwd=tmp_path,
            stdout=subprocess.DEVNULL,
        )
        shutil.copy(tmp_path / "extra_page.pdf", destination_dir)


if __name__ == "__main__":
    build_extra_page_pdf()
