# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

import json

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework import status

from plom.textools import texFragmentToPNG
from .utils import _error_response


class MlatexFragment(APIView):
    def post(self, request):
        try:
            request_json = json.loads(request.body)
            fragment = request_json.get("fragment")
        except ValueError:
            return _error_response(
                "post: Problem decoding json from client",
                status.HTTP_406_NOT_ACCEPTABLE,
            )
        except KeyError:
            return _error_response(
                "post: Json did not include required 'fragment' key",
                status.HTTP_406_NOT_ACCEPTABLE,
            )

        try:
            valid, value = texFragmentToPNG(fragment)
        except RuntimeError:
            # TODO: but I don't think texFragmentToPNG raises this, maybe in the future
            return _error_response(
                "post: Sorry server does not support latex",
                status.HTTP_406_NOT_ACCEPTABLE,
            )
        if not valid:
            return _error_response(value, status.HTTP_406_NOT_ACCEPTABLE)
        # see, for example, why to use httpresponse here instead of DRF's Response
        # https://stackoverflow.com/questions/47192986/difference-between-response-and-httpresponse-django
        return HttpResponse(value)
