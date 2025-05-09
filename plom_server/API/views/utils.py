# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023, 2025 Colin B. Macdonald
# Copyright (C) 2025 Philip D. Loewen

from rest_framework import serializers
from rest_framework.response import Response

import datetime
import pytz
import sys


def debugnote(text: str, newline: bool = False) -> None:
    """Print given text with an opening datestamp. Useful for old-style debugging.

    Args:
        text: String to print
        newline: Boolean to activate an initial newline

    Returns:
        None
    """
    myZone = "America/Vancouver"
    now = datetime.datetime.now(pytz.timezone(myZone))
    prefix = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
    print(("\n" if newline else "") + prefix + ": " + text, file=sys.stderr)
    sys.stdout.flush()  # Don't let buffering delay delivery!
    sys.stderr.flush()


def _error_response(e: Exception | str, status) -> Response:
    # status is e.g., `status.HTTP_404_NOT_FOUND`
    # I think those are int but not sure that's the right type
    r = Response(status=status)
    if isinstance(e, serializers.ValidationError):
        # Special case: this "args" hack looks better than str(e)
        # but not sure what is the "right way" to render a ValidationError
        # See also Rubrics/views.py which does a similar hack and includes
        # a more detailed example of what it looks like without this.
        #
        # Note this special case is used for `serializers.ValidationError`
        # but should *not* be used for `django.forms.ValidationError`.
        # (see Issue #3808 which discusses the two kinds)
        (r.reason_phrase,) = e.args
        return r
    r.reason_phrase = str(e)
    return r
