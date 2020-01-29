#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2020 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

print(
    """
There are two options for reassembling PDFs depending on whether or not you used Plom to mark papers.
  - the 024a script builds PDFs which have been ID'd and marked. This is the script you should use in typical situations.
  - the 024b script builds PDFs which have been ID'd but not marked. Use this script if you are using Plom for the online-return of papers that were marked offline.
"""
)
