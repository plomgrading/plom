# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023, 2025 Colin B. Macdonald

from rest_framework import serializers
from rest_framework.response import Response

import sys  # PDL wants this for debugging
import datetime


def debugnote(text: str, newline: bool = False):
    dt = datetime.timedelta(hours=-7)
    now = datetime.datetime.now() + dt
    prefix = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
    print(("\n" if newline else "") + prefix + ": " + text)
    sys.stdout.flush()
    sys.stderr.flush()


def _error_response(e: Exception | str, status) -> Response:
    debugnote("<><> _err_response: Starting.")
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
    debugnote("<><> _err_response: reason_phrase follows:\n" + r.reason_phrase)
    debugnote("<><> _err_response: Next line is return.")
    return r
