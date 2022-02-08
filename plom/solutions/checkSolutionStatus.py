# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2020-2021 Andrew Rechnitzer
# Copyright (C) 2020-2022 Colin B. Macdonald

from plom.solutions import with_manager_messenger


@with_manager_messenger
def checkStatus(*, msgr):
    """Checks the status of solutions on a server.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    Returns:
        list: each entry is a list of triples ``[q, v, md5sum]`` or
        ``[q, v, ""]``.  TODO: explain more.

    """
    return msgr.getSolutionStatus()
