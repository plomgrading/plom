#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Plom script displaying help for new users."""

__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin B. Macdonald"
__credits__ = "The Plom Project Developers"
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from plom import __version__
from textwrap import dedent


def main():
    print("Plom version {}".format(__version__))

    print(
        dedent(
            """
    To get started, go here:

        https://plom.gitlab.io/
    """
        )
    )


if __name__ == "__main__":
    main()
