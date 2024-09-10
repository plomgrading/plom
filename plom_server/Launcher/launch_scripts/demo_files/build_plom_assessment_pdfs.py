#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
from tempfile import NamedTemporaryFile

# need these imports to get idBox template from plom
import plom
import sys

if sys.version_info >= (3, 9):
    from importlib import resources
else:
    import importlib_resources as resources


def compile_tex(filepath: Path) -> None:
    # make sure the idbox file is in place
    idbox_filepath = filepath.parent / "idBox4.pdf"
    if not idbox_filepath.exists():
        idbox_bytes = (resources.files(plom) / "idBox4.pdf").read_bytes()
        with idbox_filepath.open("wb") as fh:
            fh.write(idbox_bytes)
    # now get on with building the .tex
    filestem = filepath.stem
    # use latexmk to build, continue past errors, and then
    # clean up all files except the .tex and .pdf
    subprocess.run(
        ["latexmk", "-pdf", "-silent", "-interaction=nonstopmode", f"{filestem}"],
        check=True,
    )
    subprocess.run(["latexmk", "-silent", "-c", f"{filestem}"], check=True)
    # finally, remove the idbox
    idbox_filepath.unlink(missing_ok=True)


def compile_tex_str_to_filepath(tex_as_str: str, pdf_filepath: Path) -> None:
    # open and write to a temp-file
    tmp_tex_file = NamedTemporaryFile(
        mode="w", suffix=".tex", dir=pdf_filepath.parent, delete=False
    )
    tmp_tex_file.write(tex_as_str)
    tmp_tex_file.close()
    # compile the temp file
    tmp_tex_path = Path(tmp_tex_file.name)
    compile_tex(tmp_tex_path)
    # move the resulting .pdf into place
    # note that shutil move and pathlib typing error - https://bugs.python.org/issue39140
    # fixed in python 3.9 - so our mypy will throw an error on the following line
    shutil.move(tmp_tex_path.with_suffix(".pdf"), pdf_filepath)  # type: ignore
    # now clean up the temp file
    tmp_tex_path.unlink(missing_ok=True)


def build_with_without_soln(filename_without_suffix: str) -> None:
    source_path = Path(filename_without_suffix)
    source_path_tex = source_path.with_suffix(".tex")
    if source_path_tex.exists():
        pass
    else:
        raise ValueError(f"Cannot open file {source_path_tex}")

    # read in the .tex as a big string
    with source_path_tex.open("r") as fh:
        original_data = fh.read()

    # comment out the '\printanswers'  line
    no_soln_data = re.sub(r"\\printanswers", r"% \\printanswers", original_data)
    no_soln_pdf_filepath = source_path.with_suffix(".pdf")
    compile_tex_str_to_filepath(no_soln_data, no_soln_pdf_filepath)
    # remove any %-comments on line with '\printanswers'
    yes_soln_data = re.sub(r"%\s+\\printanswers", r"\\printanswers", original_data)
    yes_soln_pdf_filepath = Path(source_path.stem + "_solutions.pdf")
    compile_tex_str_to_filepath(yes_soln_data, yes_soln_pdf_filepath)


if __name__ == "__main__":
    sources = ["assessment_v1", "assessment_v2"]
    for filename in sources:
        build_with_without_soln(filename)
