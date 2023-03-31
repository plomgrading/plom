# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status


class MlatexFragment(APIView):
    # TODO: in legacy there is a "fragment" key for this get, Issue #2371
    # TODO: is 406 ok for a placeholder, Issue #2638
    # TODO: port the service from legacy, Issue #2639

    def get(self, request):
        print("latex not implemented yet, Issue #2639")
        return Response(
            "Sorry server does not support latex", status=status.HTTP_406_NOT_ACCEPTABLE
        )
