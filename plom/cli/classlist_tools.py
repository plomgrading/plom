# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

import sys
from pathlib import Path

from plom.cli import with_messenger

from plom.plom_exceptions import PlomAuthenticationException, PlomConflict


@with_messenger
def download_classlist(msgr) -> bool:
    """Copy the server's classlist to stdout in CSV format.

    Args:
        msgr:  An active Messenger object.
    """
    sys.stdout.write("CSV coming soon!\n")
    waste_some_bits = Path("/dev/null")
    if False:
        raise PlomConflict from None
    else:
        raise PlomAuthenticationException from None

    return waste_some_bits
