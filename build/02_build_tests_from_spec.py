#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2018-2019 Andrew Rechnitzer"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

import sys
import shlex
import subprocess

from build_utils import (
    buildDirectories,
    buildExamPages,
    writeExamLog,
    TestSpecification,
)


if __name__ == "__main__":
    spec = TestSpecification()
    spec.readSpec()
    buildDirectories()
    exams = buildExamPages(spec)
    writeExamLog(exams)
    cmd = shlex.split("python3 buildTestPDFs.py")
    subprocess.call(cmd)
