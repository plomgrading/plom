# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald

from typing import Dict, Any

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status

from plom import __version__
from plom import Plom_API_Version

from Mark.services import MarkingTaskService
from Identify.services import IdentifyTaskService
from Papers.services import SpecificationService


class GetSpecification(APIView):
    """Return the public part of the specification.

    Returns:
        (200) JsonResponse: the spec
        (400) spec not found
    """

    def get(self, request):
        spec = SpecificationService()
        if not spec.is_there_a_spec():
            return Response(
                "Server does not have a spec", status=status.HTTP_400_BAD_REQUEST
            )

        the_spec = spec.get_the_spec()
        the_spec.pop("privateSeed", None)

        return Response(the_spec)


def _version_string():
    return f"Plom server version {__version__} with API {Plom_API_Version}"


class ServerVersion(APIView):
    """Get the server version.

    Returns:
        (200): and the version string as ``text/plain``, not JSON.
    """

    def get(self, request):
        return HttpResponse(_version_string(), content_type="text/plain")


class ServerInfo(APIView):
    """Get the server software information such as version in extensible format.

    Returns:
        (200): a dict of information about the server as key-value pairs,
    """

    def get(self, request):
        info: Dict[str, Any] = {
            "product_string": "Plom Server",
            "version": __version__,
            "API_version": Plom_API_Version,
            "version_string": _version_string(),
            # TODO: "acceptable_client_API": [100, 101, 107],
        }
        return Response(info)


class CloseUser(APIView):
    """Delete the user's token and log them out.

    Returns:
        (200) user is logged out successfully
        (401) user is not signed in
    """

    def delete(self, request):
        try:
            request.user.auth_token.delete()

            mts = MarkingTaskService()
            mts.surrender_all_tasks(request.user)

            its = IdentifyTaskService()
            its.surrender_all_tasks(request.user)

            return Response(status=status.HTTP_200_OK)
        except (ValueError, ObjectDoesNotExist, AttributeError):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
