#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2019 Andrew Rechnitzer and Colin Macdonald"
__credits__ = ["Andrew Rechnitzer", "Colin Macdonald"]
__license__ = "AGPL-3.0-or-later"
# SPDX-License-Identifier: AGPL-3.0-or-later

from specParser import SpecVerifier, SpecParser

sv = SpecVerifier()
sv.verifySpec()
sv.checkCodes()
sv.saveVerifiedSpec()

sp = SpecParser()
sp.printSpec()
