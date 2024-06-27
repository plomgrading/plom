# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2019-2022 Andrew Rechnitzer
# Copyright (C) 2020-2024 Colin B. Macdonald
# Copyright (C) 2022 Michael Deakin
# Copyright (C) 2024 Aden Chan


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


class PlomSSLError(PlomBenignException):
    pass


class PlomConnectionError(PlomBenignException):
    pass


class PlomConflict(PlomBenignException):
    """The action was contradictory to info already in the system."""

    pass


class PlomDependencyConflict(PlomConflict):
    """Attempt to modify an object on which other objects depend."""

    pass


class PlomNoMoreException(PlomBenignException):
    pass


class PlomRangeException(PlomBenignException):
    pass


class PlomVersionMismatchException(PlomBenignException):
    pass


class PlomBadTagError(PlomBenignException):
    pass


class PlomDatabaseCreationError(PlomBenignException):
    pass


class PlomExistingDatabase(PlomBenignException):
    """The database has already been populated."""

    def __init__(self, msg=None):
        if not msg:
            msg = "Database already populated"
        super().__init__(msg)


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


class PlomUnidentifiedPaperException(PlomBenignException):
    pass


class PlomUnscannedPaper(PlomBenignException):
    pass


class PlomTaskChangedError(PlomBenignException):
    pass


class PlomTaskDeletedError(PlomBenignException):
    pass


class PlomForceLogoutException(PlomSeriousException):
    """We call this when the server has changed or deleted a task out from under the client."""

    pass


class PlomNoSolutionException(PlomBenignException):
    pass


class PlomServerNotReady(PlomBenignException):
    """For example if it has no spec."""

    pass


class PlomNoClasslist(PlomServerNotReady):
    pass


class PlomNoRubric(PlomSeriousException):
    pass


class PlomInconsistentRubric(PlomSeriousException):
    pass


class PlomInvalidRubric(PlomSeriousException):
    pass


class PlomTimeoutError(PlomSeriousException):
    """Some message failed due to network trouble such as a timeout.

    TODO: currently a PlomSeriousException but consider making this
    a PlomBenignException later.
    """

    pass


class PlomNoPaper(PlomBenignException):
    """Plom doesn't have a paper."""

    pass


class PlomNoPermission(PlomBenignException):
    """You don't have permission, e.g.., for that paper, rubric, etc."""

    pass


class PlomBundleLockedException(PlomBenignException):
    """For when a bundle is locked or pushed."""

    pass


class PlomNoServerSupportException(PlomBenignException):
    """For when an action is not supported by the server."""

    pass
