#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

print(
    """
To start the build process

  0. Find your source PDFs and copy them to the "sourceVersions" directory
     as version1.pdf, version2.pdf, etc

  1. Copy the file "template_testSpec.toml" to "testSpec.toml" and edit
     using your favourite text editor.

  2. Run the "002_verifySpec.py" script
  3. Run the "003_buildPlomDB.py" script
  4. Run the "004_buildPDFs.py" script
"""
)
