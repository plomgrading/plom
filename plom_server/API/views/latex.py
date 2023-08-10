# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from plom.textools import texFragmentToPNG
from .utils import _error_response


class MlatexFragment(APIView):
    def post(self, request):
        try:
            fragment = request.data["fragment"]
        except KeyError as e:
            return _error_response(
                f"post: json not as required: {e}", status.HTTP_400_BAD_REQUEST
            )

        try:
            valid, value = texFragmentToPNG(fragment)
        except RuntimeError:
            # TODO: but I don't think texFragmentToPNG raises this, maybe in the future
            valid = False
            value = "Sorry server does not support latex"
        if not valid:
            r = {"error": True, "tex_output": value}
            return Response(r, status=status.HTTP_406_NOT_ACCEPTABLE)
        # see, for example, why to use httpresponse here instead of DRF's Response
        # https://stackoverflow.com/questions/47192986/difference-between-response-and-httpresponse-django
        # TODO: maybe in future, we pack it uuencoded inside json, include the tex output etc
        return HttpResponse(value)
