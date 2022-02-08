# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2021-2022 Colin B. Macdonald

from plom.plom_exceptions import PlomNoSolutionException
from plom.solutions import with_manager_messenger


@with_manager_messenger
def getSolutionImage(question, version, *, msgr):
    """Get a solution image from the server.

    Args:
        question (int): which question.
        version (int): which version.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    Return:
        bytes/None: the bitmap of the solution or None if there was no
        solution.  TODO: consider using an exception instead.
    """
    try:
        return msgr.getSolutionImage(question, version)
    except PlomNoSolutionException as err:
        print(err)
        return None
