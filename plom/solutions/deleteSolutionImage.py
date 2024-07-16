# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2021 Andrew Rechnitzer
# Copyright (C) 2022, 2024 Colin B. Macdonald

from plom.solutions import with_manager_messenger
from plom.plom_exceptions import PlomNoSolutionException


@with_manager_messenger
def deleteSolutionImage(question, version, *, msgr):
    """Delete one of the solution images on the server.

    Args:
        question (int): which question.
        version (int): which version.

    Keyword Args:
        msgr (plom.Messenger/tuple): either a connected Messenger or a
            tuple appropriate for credientials.

    Returns:
        None

    Raises:
        PlomNoSolutionException: the question/version asked for does
            not have a solution image on the server.  This is also
            raised if the values are out of range.
    """
    if msgr.deleteSolutionImage(question, version):
        return
    raise PlomNoSolutionException(
        f"Server has no solution to question {question} version {version} to remove"
    )
