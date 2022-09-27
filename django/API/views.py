# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from Papers.services import SpecificationService
from API.models import NumberToIncrement


class InfoSpec(APIView):
    """
    Return the public part of the specification.

    Returns:
        (200) JsonResponse: the spec
        (400) spec not found
    """

    def get(self, request):
        spec = SpecificationService()
        if not spec.is_there_a_spec():
            exc = APIException()
            exc.status_code = status.HTTP_400_BAD_REQUEST
            exc.detail = "Server does not have a spec."
            raise exc

        the_spec = spec.get_the_spec()
        the_spec.pop("privateSeed", None)
        the_spec.pop("publicCode", None)

        return Response(the_spec)


class NumberIncrement(APIView):
    """
    The user can view or increment a number.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_number, created = NumberToIncrement.objects.get_or_create(user=user)
        response_dict = {"number": user_number.number, "created": created}
        return Response(response_dict)

    def post(self, request):
        user = request.user
        user_number, created = NumberToIncrement.objects.get_or_create(user=user)
        user_number.number += 1
        user_number.save()
        response_dict = {"number": user_number.number, "created": created}
        return Response(response_dict)
