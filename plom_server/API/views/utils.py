# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023, 2025 Colin B. Macdonald

from rest_framework import serializers
from rest_framework.response import Response


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
