# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2020 Andrew Rechnitzer
# Copyright (C) 2020 Colin B. Macdonald


"""Exceptions for the Plom software.

Serious exceptions are for unexpected things that we probably cannot
sanely or safely recover from.  Benign are for signaling expected (or
at least not unexpected) situations.
"""


class PlomException(Exception):
    """Catch-all parent of all Plom-related exceptions."""

    pass


class PlomSeriousException(PlomException):
    """Serious or unexpected problems that are generally not recoverable."""

    pass


class PlomBenignException(PlomException):
    """A not-unexpected situation, often signaling an error condition."""

    pass


class PlomAPIException(PlomBenignException):
    pass


class PlomConflict(PlomBenignException):
    """The action was contradictory to info already in the system."""

    pass


class PlomNoMoreException(PlomBenignException):
    pass


class PlomRangeException(PlomBenignException):
    pass


class PlomAuthenticationException(PlomBenignException):
    """You are not authenticated, with precisely that as the default message."""

    def __init__(self, msg=None):
        if not msg:
            msg = "You are not authenticated."
        super().__init__(msg)


class PlomTakenException(PlomBenignException):
    pass


class PlomLatexException(PlomBenignException):
    pass


class PlomExistingLoginException(PlomBenignException):
    pass


class PlomOwnersLoggedInException(PlomBenignException):
    pass


class PlomTaskChangedError(PlomBenignException):
    pass


class PlomTaskDeletedError(PlomBenignException):
    pass
