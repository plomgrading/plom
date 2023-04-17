#!/bin/env -S python3 -u

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

"""Divide the Plom "papersToPrint" into bins based on a spreadsheet.

You build a spreadsheet with columns "room dir name", "start", and "end"
(other columns ok too; they will be ignored).

We open it, then iterate over the rows, making directories inside
"dirsToPrint" and moving the pdf files from "papersToPrint".
"""

import argparse
import shutil
from pathlib import Path

import pandas as pd


__script_version__ = "0.0.1"


def get_parser():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        epilog="\n".join(__doc__.split("\n")[1:]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__script_version__}"
    )
    parser.add_argument(
        "--outdir",
        type=str,
        action="store",
        help="""
            Base output directory, defaults to "dirsToPrint" under
            the current directory if unspecified.  Will be created
            automatically.
        """,
    )
    parser.add_argument(
        "--indir",
        type=str,
        action="store",
        help="""
            Where to find Plom's pdf files.  Defaults to "papersToPrint"
            under the current directory if unspecified.
        """,
    )
    parser.add_argument(
        "--csv",
        type=str,
        action="store",
        help="""
            Name of a CSV file (or probably anything else that the
            Pandas library can load).  If omitted, defaults to
            "papers_to_rooms.csv".
        """,
    )

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    if not args.csv:
        args.csv = "papers_to_rooms.csv"
    args.csv = Path(args.csv)
    if not args.indir:
        args.indir = "papersToPrint"
    args.indir = Path(args.indir)
    if not args.outdir:
        args.outdir = Path("dirsToPrint")
    args.outdir = Path(args.outdir)

    df = pd.read_csv(args.csv, dtype=object)
    print(df)

    args.outdir.mkdir(exist_ok=True)
    for idx, row in df.iterrows():
        subdir = row["room dir name"]
        start = int(row["start"])
        stop = int(row["end"])
        print(f"working on dir {subdir!r}, moving {start} to {stop}")
        (args.outdir / subdir).mkdir(exist_ok=True)
        for n in range(start, stop + 1):
            (f,) = args.indir.glob(f"exam_{n:04}*.pdf")
            # not pathlib.rename in case 'out' is different file system
            # shutil.move(f, args.outdir / subdir)
            # (ugh, python 3.8 needs strings here)
            shutil.move(str(f), str(args.outdir / subdir))


if __name__ == "__main__":
    main()
