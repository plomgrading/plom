#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024-2025 Colin B. Macdonald
# Copyright (C) 2024 Andrew Rechnitzer

import argparse
import re
import shutil
import subprocess
from importlib import resources
from pathlib import Path
from tempfile import NamedTemporaryFile

# we get the idBox template from Plom's resources
import plom


def _actually_compile_tex(filepath: Path) -> None:
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
        ["latexmk", "-pdf", "-interaction=nonstopmode", f"{filestem}"], check=True
    )
    subprocess.run(["latexmk", "-c", f"{filestem}"], check=True)
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
    _actually_compile_tex(tmp_tex_path)
    # move the resulting .pdf into place
    shutil.move(tmp_tex_path.with_suffix(".pdf"), pdf_filepath)
    # now clean up the temp file
    tmp_tex_path.unlink(missing_ok=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "filename",
        help="the latex file to compile --- assumes is in current directory.",
    )
    args = p.parse_args()

    source_path = Path(args.filename)
    if source_path.suffix == ".tex":
        pass
    elif source_path.suffix == "":
        source_path = source_path.with_suffix(".tex")
    else:
        raise ValueError(
            f"Cannot proce file {source_path} with suffix {source_path.suffix}"
        )
    if source_path.exists():
        pass
    else:
        raise ValueError(f"Cannot open file {source_path}")

    # read in the .tex as a big string
    with source_path.open("r") as fh:
        original_data = fh.read()

    # comment out the '\printanswers'  line
    no_soln_data = re.sub(r"\\printanswers", r"% \\printanswers", original_data)
    no_soln_pdf_filepath = source_path.with_suffix(".pdf")
    compile_tex_str_to_filepath(no_soln_data, no_soln_pdf_filepath)
    # remove any %-comments on line with '\printanswers'
    yes_soln_data = re.sub(r"%\s+\\printanswers", r"\\printanswers", original_data)
    yes_soln_pdf_filepath = Path(source_path.stem + "_solutions.pdf")
    compile_tex_str_to_filepath(yes_soln_data, yes_soln_pdf_filepath)
