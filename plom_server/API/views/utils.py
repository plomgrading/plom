# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from typing import Union

# from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError


def _error_response(e: Union[Exception, str], status) -> Response:
    # status is e.g., `status.HTTP_404_NOT_FOUND`
    # I think those are int but not sure that's the right type
    r = Response(status=status)
    if isinstance(e, ValidationError):
        # special case: looks better than str(e)
        (r.reason_phrase,) = e.args
        return r
    r.reason_phrase = str(e)
    return r
