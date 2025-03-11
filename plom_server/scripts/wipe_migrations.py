#!/usr/bin/env python3

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Andrew Rechnitzer
# Copyright (C) 2024-2025 Colin B. Macdonald

import argparse
from pathlib import Path

# from django.conf import settings


def remove_all_migration_files(basedir: Path, *, verbose: bool = True) -> None:
    """Remove old db migration files from the source tree.

    Caution: this assumes we have read-write access to the source code!
    """
    if verbose:
        print(f"Removing autogen migration files from {basedir}")
    for path in basedir.glob("*/migrations/*.py"):
        if path.name == "__init__.py":
            continue
        if verbose:
            print(f"Removing {path}")
            path.unlink(missing_ok=True)


def set_argparse_and_get_args() -> argparse.Namespace:
    """Configure argparse to collect commandline options."""
    parser = argparse.ArgumentParser(
        description="""
            Remove all the migration files, in preparation for regenerating from scratch
        """,
    )
    parser.add_argument(
        "--basedir",
        action="store",
        default="plom_server",
        help="Search for all migrations under this directory.",
    )

    return parser.parse_args()


def main():
    """Remove all the migration files, in preparation for regenerating from scratch."""
    # This would be a good default, but this script does not depend on Django
    # basedir = settings.BASE_DIR

    args = set_argparse_and_get_args()
    remove_all_migration_files(Path(args.basedir))


if __name__ == "__main__":
    main()
