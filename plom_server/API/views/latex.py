# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

import json
from django.http import HttpResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status

from plom.textools import texFragmentToPNG


class MlatexFragment(APIView):
    def post(self, request):
        try:
            request_json = json.loads(request.body)
            fragment = request_json.get("fragment")
        except ValueError:
            return Response(
                "post: Problem decoding json from client",
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        except KeyError:
            return Response(
                "post: Json did not include required 'fragment' key",
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        try:
            valid, value = texFragmentToPNG(fragment)
        except RuntimeError:
            return Response(
                "post: Sorry server does not support latex",
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
        if valid:
            # see https://stackoverflow.com/questions/47192986/difference-between-response-and-httpresponse-django   (for example)
            # for why to use httpresponse here instead of DRF's Response
            return HttpResponse(value)
        else:
            return Response(
                value,
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )
