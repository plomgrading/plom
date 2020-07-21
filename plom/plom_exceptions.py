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

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class PlomSeriousException(PlomException):
    """Serious or unexpected problems that are generally not recoverable."""

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class PlomBenignException(PlomException):
    """A not-unexpected situation, often signallying an error condition."""

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomAPIException(PlomBenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomConflict(PlomBenignException):
    """The action was contradictory to info already in the system."""

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomNoMoreException(PlomBenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomRangeException(PlomBenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomAuthenticationException(PlomBenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, "You are not authenticated.", *args, **kwargs)


class PlomTakenException(PlomBenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomLatexException(PlomBenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomExistingLoginException(PlomBenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomTaskChangedException(PlomBenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


class PlomTaskDeletedException(PlomBenignException):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
