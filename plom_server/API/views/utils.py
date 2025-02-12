# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023, 2025 Colin B. Macdonald

from django.forms import ValidationError
from rest_framework import serializers
from rest_framework.response import Response


def _error_response(e: Exception | str, status) -> Response:
    # status is e.g., `status.HTTP_404_NOT_FOUND`
    # I think those are int but not sure that's the right type
    r = Response(status=status)
    if isinstance(e, serializers.ValidationError):
        # special case: looks better than str(e)
        (r.reason_phrase,) = e.args
        return r
    if isinstance(e, ValidationError):
        # TODO: does this really need a special case?
        # By accident in Issue #3808 it did NOT have a special case...?
        print(f"DEBUG XXXX: does this need a special case?\n{e}\n{str(e)}")
        (r.reason_phrase,) = e.args
        return r
    r.reason_phrase = str(e)
    return r
