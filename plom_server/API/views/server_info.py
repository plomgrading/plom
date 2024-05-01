# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import update_last_login
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from plom import __version__
from plom import Plom_API_Version
from plom.feedback_rules import feedback_rules

from API.permissions import AllowAnyReadOnly

from Mark.services import MarkingTaskService
from Identify.services import IdentifyTaskService
from Papers.services import SpecificationService

from .utils import _error_response


class GetSpecification(APIView):
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


def _version_string() -> str:
    return f"Plom server version {__version__} with API {Plom_API_Version}"


class ServerVersion(APIView):
    """Get the server version.

    Returns:
        (200): and the version string as ``text/plain``, not JSON.
    """

    permission_classes = [AllowAnyReadOnly]

    def get(self, request: Request) -> HttpResponse:
        return HttpResponse(_version_string(), content_type="text/plain")


class ServerInfo(APIView):
    """Get the server software information such as version in extensible format.

    Returns:
        (200): a dict of information about the server as key-value pairs,
    """

    permission_classes = [AllowAnyReadOnly]

    def get(self, request: Request) -> Response:
        info: dict[str, Any] = {
            "product_string": "Plom Server",
            "version": __version__,
            "API_version": Plom_API_Version,
            "version_string": _version_string(),
            # TODO: "acceptable_client_API": [100, 101, 107],
        }
        return Response(info)


class ExamInfo(APIView):
    """Get the assessment information in an extensible format.

    Returns:
        (200): a dict of information about the exam/assessment as
           key-value pairs,
    """

    def get(self, request: Request) -> Response:
        # TODO: hardcoded, and needs more info, Issue #2938
        # TODO: suggest progress info here too
        info: dict[str, Any] = {
            "current_largest_paper_num": 9999,
            "feedback_rules": feedback_rules,
        }
        return Response(info)


class CloseUser(APIView):
    """Delete the user's token and log them out.

    Returns:
        (200) user is logged out successfully
        (401) user is not signed in
    """

    def surrender_tasks_and_logout(self, user_obj):
        # if user has an auth token then delete it
        try:
            user_obj.auth_token.delete()
        except Token.DoesNotExist:
            # does not have a token, no need to delete.
            pass

        MarkingTaskService().surrender_all_tasks(user_obj)
        IdentifyTaskService().surrender_all_tasks(user_obj)

    def delete(self, request):
        try:
            self.surrender_tasks_and_logout(request.user)
            return Response(status=status.HTTP_200_OK)
        except (ValueError, ObjectDoesNotExist, AttributeError):
            return Response(status=status.HTTP_401_UNAUTHORIZED)


class ObtainAuthTokenUpdateLastLogin(ObtainAuthToken):
    """Overrides the DRF auth-token creator so that it updates the user last_login field, and does an API version check."""

    # Idea from
    # https://stackoverflow.com/questions/28613102/last-login-field-is-not-updated-when-authenticating-using-tokenauthentication-in
    # and https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Login a user from the client, provided they have given us an appropriate client version.

        Returns:
            200 and a token in json if user logged in successfully.
            401 for bad client version.  400 for poorly formed requests,
            such as no client version.  Legacy used to send 409 if user
            was already logged in but currently that may not be enforced.
        """
        # TODO: probably serializer supposed to do something but ain't nobody got time for that
        client_api = request.data.get("api")
        client_ver = request.data.get("client_ver")
        if not client_api:
            # TODO: should I log and how to log in django?
            # log.warn(f"login from old client {client_ver} that speaks API {client_api}")
            return _error_response(
                "Client did not report their API version", status.HTTP_400_BAD_REQUEST
            )

        if not client_ver:
            return _error_response(
                "Client did not report their version", status.HTTP_400_BAD_REQUEST
            )

        # should the serializer should be doing this?
        if not client_api.isdigit():
            return _error_response(
                f'Client sent non-integer API version: "{client_api}"',
                status.HTTP_400_BAD_REQUEST,
            )

        # TODO: use >= and check client side, Issue #3247
        if not int(client_api) == int(Plom_API_Version):
            return _error_response(
                f"Client API version {client_api} is not supported by this server "
                f"(server API version {Plom_API_Version})",
                status.HTTP_401_UNAUTHORIZED,
            )

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        update_last_login(None, token.user)
        return Response({"token": token.key})
