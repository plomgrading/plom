# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2018-2024 Andrew Rechnitzer
# Copyright (C) 2020-2026 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2024 Aden Chan

# Any utilities that don't have there own version can use this one
# Also in plom_server/__init__.py
__version__ = "0.20.1"

import sys

# probably we don't need this sort of thing any more, but doesn't hurt...?
if sys.version_info[0] == 2:
    raise RuntimeError("Plom requires Python 3; it will not work with Python 2")

Default_Port = 41984
