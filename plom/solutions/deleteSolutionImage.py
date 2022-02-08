# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2022 Colin B. Macdonald

from plom.plom_exceptions import PlomNoSolutionException
from plom.solutions import with_manager_messenger


@with_manager_messenger
def deleteSolutionImage(question, version, *, msgr):
    """Delete one of the solution images on the server.

    Args:
        question (int): which question.
        version (int): which version.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    Return:
        bool/None: `True` on success, `None` on failure b/c no solution.
        TODO: change and/or consider using exception on failure.
    """
    try:
        return msgr.deleteSolutionImage(question, version)
    except PlomNoSolutionException:
        print("No solution for question {} version {}".format(question, version))
        return None
