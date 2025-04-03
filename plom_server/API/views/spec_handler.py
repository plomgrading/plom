# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from Papers.services import SpecificationService
from .utils import _error_response


class SpecificationHandler(APIView):
    """Return the public part of the specification.

    Returns:
        (200) JsonResponse: the spec
        (400) spec not found
    """

    def get(self, request: Request) -> Response:
        if not SpecificationService.is_there_a_spec():
            return _error_response(
                "Server does not have a spec", status.HTTP_400_BAD_REQUEST
            )

        the_spec = SpecificationService.get_the_spec()
        the_spec.pop("privateSeed", None)

        return Response(the_spec)

    def post(self, request: Request) -> Response:
        # Copy working text in here.
        return Response("Not implemented yet.")
