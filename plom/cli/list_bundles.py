# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from tabulate import tabulate

from plom.cli import with_messenger


@with_messenger
def list_bundles(*, msgr):
    """Prints summary of test/hw uploads.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.
    """
    st = msgr.new_server_list_bundles()
    # , tablefmt="simple_outline")
    print(tabulate(st, headers="firstrow"))
