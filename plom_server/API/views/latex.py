# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status

from plom.textools import texFragmentToPNG


class MlatexFragment(APIView):
    def post(self, request):
        print("latex not implemented yet, Issue #2639")
        print(request)
        data = request.POST
        print(data)
        fragment = data.get("fragment")
        valid, value = texFragmentToPNG(fragment)
        print(fragment)
        print(valid)
        print(type(valid))
        print(type(value))
        print(len(value))
        return Response(
            "post: Sorry server does not support latex",
            status=status.HTTP_406_NOT_ACCEPTABLE,
        )
