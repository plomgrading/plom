#!/usr/bin/env python3
# Copyright (C) 2020 Andrew Rechnitzer
# Copyright (C) 2020-2021, 2023 Colin B. Macdonald
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Plom script displaying help for new users."""

__copyright__ = "Copyright (C) 2020-2023 Andrew Rechnitzer, Colin B. Macdonald, et al"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"

import argparse
from textwrap import dedent

from plom import __version__


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__
    )
    args = parser.parse_args()

    print("Plom version {}".format(__version__))

    print(
        dedent(
            """
    To get started, go here:

        https://plomgrading.org
    """
        )
    )


if __name__ == "__main__":
    main()
