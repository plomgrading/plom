# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from typing import Any

from django.contrib.auth.models import update_last_login, User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status

from plom_server import Plom_API_Version
from plom_server import __version__
from plom_server.Base.services import Settings
from plom_server.Mark.services import MarkingTaskService
from plom_server.Identify.services import IdentifyTaskService
from ..permissions import AllowAnyReadOnly
from ..services import TokenService
from .utils import _error_response


def _version_string() -> str:
    return f"Plom server version {__version__} with API {Plom_API_Version}"


def _client_reject_list() -> list[dict[str, Any]]:
    # Explanation of fields
    # ---------------------
    # "client-id": something unique to tell different clients apart,
    #     currently there is only "org.plomgrading.PlomClient".
    # "operator" defaults to "==" if omitted, can also be "<",
    #     ">", "<=" or ">=".
    # "version" must be something parsable by `Version` from
    #     `packaging.version`.
    # "action", can be "warn" or "block".  Should be assumed to be
    #     "block" if omitted.
    # "reason": optional but recommended explanation, it should
    #     be polite and end with something like "please upgrade".
    #     It might be rendered in HTML, so avoid `<`, `>`, `&`.
    #
    # This is not the only mechanism to keep out old clients: there
    # also an "API version" that clients must match.
    #
    # Examples
    # --------
    #
    # {
    #    "client-id": "org.plomgrading.PlomClient",
    #    "version": "0.16.3",
    #    "operator": "<",
    #    "reason": "0.16.4 fixed important bugs; older clients not recommended, please upgrade.",
    #    "action": "warn",
    # },
    # {
    #    "client-id": "org.plomgrading.PlomClient",
    #    "version": "0.16.7",
    #    "operator": "==",
    #    "reason": "0.16.7 has a show-stopper bug; please upgrade (or downgrade).",
    #    "action": "warn",
    # },

    return [
        {
            "client-id": "org.plomgrading.PlomClient",
            "version": "0.16.7",
            "operator": "==",
            "reason": (
                "This is just an example; 0.16.x will be blocked by API anyway."
                "Please upgrade (or downgrade)."
            ),
            "action": "warn",
        },
        {
            "client-id": "org.plomgrading.PlomClient",
            "version": "0.19.1",
            "operator": "<=",
            "reason": (
                "Plom Client v0.19.0 and v0.19.1 cannot be safely used "
                "to mark paper numbers larger than 999."
                " Please upgrade your client to v0.19.2 or later."
            ),
            "action": "block",
        },
    ]


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
            "client-reject-list": _client_reject_list(),
        }
        return Response(info)


class UserRole(APIView):
    """Get the user's role.

    Returns:
        either of ["lead_marker", "marker", "scanner", "manager"] if the user
            is recognized. Otherwise returns None.
    """

    def get(self, request: Request, *, username: str) -> HttpResponse:
        role = self._get_user_role(username)
        return HttpResponse(role, content_type="text/plain")

    def _get_user_role(self, username: str) -> str | None:
        user = User.objects.get(username__iexact=username)
        group = user.groups.values_list("name", flat=True)
        if "lead_marker" in group:
            return "lead_marker"
        elif "marker" in group:
            return "marker"
        elif "manager" in group:
            return "manager"
        elif "scanner" in group:
            return "scanner"
        else:
            return None


class ExamInfo(APIView):
    """Get the assessment information in an extensible format.

    Returns:
        (200): a dict of information about the assessment and
        marking settings as key-value pairs.  Currently includes
        ``current_largest_paper_num`` and ``feedback_rules``.
    """

    def get(self, request: Request) -> Response:
        # TODO: who_can_create_rubrics
        # TODO: who_can_modify_rubrics
        # TODO: suggest progress info here too
        info: dict[str, Any] = {
            # TODO: hardcoded, Issue #2938
            "current_largest_paper_num": 9999,
            "feedback_rules": Settings.get_feedback_rules(),
        }
        return Response(info)


class CloseUser(APIView):
    """Delete the user's token, surrender their tasks, and log them out."""

    # DELETE: /close_user/
    # DELETE: /close_user/?revoke_token
    def delete(self, request: Request) -> Response:
        """Token-based logout, surrender all tasks, and optionally revoke the token.

        If the ``query_params`` contains ``revoke_token`` then we'll revoke the token
        preventing future API calls until login creates a new token.

        Returns:
            Http return code 200 when the user is logged out successfully.
            A 401 error is returned in various error cases.
        """
        revoke_token = False
        if "revoke_token" in request.query_params:
            revoke_token = True
        try:
            MarkingTaskService.surrender_all_tasks(request.user)
            IdentifyTaskService.surrender_all_tasks(request.user)
            if revoke_token:
                TokenService.drop_api_token(request.user)
            return Response(status=status.HTTP_200_OK)
        except (ValueError, ObjectDoesNotExist, AttributeError):
            return Response(status=status.HTTP_401_UNAUTHORIZED)


class ObtainAuthTokenUpdateLastLogin(ObtainAuthToken):
    """Overrides the DRF auth-token creator so that it updates the user last_login field, and does an API version check."""

    # POST: /get_token/
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Request a token for a user, used to access the client-side API, provided they have given us an appropriate client version.

        In addition to "username" and "password", the request must contain
        the data "api" (and int or string) and string "client_ver".
        Optionally it can contain the data "want_exclusive_access" (a boolean)
        where True specifies that they want a brand-new unused token.
        Such callers may also want to destroy the token when they logout,
        typically by passing "revoke_token" to CloseUser.

        Returns:
            200 and a token in json if user logged in successfully.
            400 for poorly formed requests, such as no client version or bad client version.
            401 for requests with an inactive (or invalid) user/passwd combo.
            409 if the caller asks for exclusive access but already has a token (see Issue #3845).
        """
        # Idea from
        # https://stackoverflow.com/questions/28613102/last-login-field-is-not-updated-when-authenticating-using-tokenauthentication-in
        # and https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication

        # TODO: probably serializer supposed to do something but ain't nobody got time for that
        client_api = request.data.get("api")
        client_ver = request.data.get("client_ver")
        if not client_api:
            # TODO: should I log and how to log in django? (Issue #2642)
            # log.warn(f"login from old client {client_ver} that speaks API {client_api}")
            return _error_response(
                "Client did not report their API version", status.HTTP_400_BAD_REQUEST
            )

        if not client_ver:
            return _error_response(
                "Client did not report their version", status.HTTP_400_BAD_REQUEST
            )

        # should the serializer be doing this?
        try:
            client_api = int(client_api)
        except (ValueError, TypeError) as e:
            return _error_response(
                f'Client sent non-integer API version: "{client_api}": {e}',
                status.HTTP_400_BAD_REQUEST,
            )

        # note if client is more recent then their responsibility to check compat
        if client_api < int(Plom_API_Version):
            return _error_response(
                f"Client API version {client_api} is too old for this server "
                f"(server API version {Plom_API_Version})",
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return _error_response(
                "Access denied. Check username, password, and 'enabled' status.",
                status.HTTP_401_UNAUTHORIZED,
            )
        user = serializer.validated_data["user"]

        # TODO: probably fine for multiple sessions to share a token, see Issue #3845
        # and discussion there-in.  If changing this, look at delete carefully as well.
        want_exclusive_access = request.data.get("want_exclusive_access", None)
        if want_exclusive_access:
            try:
                Token.objects.get(user=user)
                return _error_response(
                    "Caller asked for exclusive access but this user already has a token:"
                    " perhaps logged in elsewhere, or there was crash."
                    ' You will need to "clear" the login to remove the pre-existing token.',
                    status.HTTP_409_CONFLICT,
                )
            except Token.DoesNotExist:
                pass
        token, created = Token.objects.get_or_create(user=user)
        update_last_login(None, token.user)
        return Response({"token": token.key})

    # DELETE: /get_token/
    def delete(self, request: Request) -> Response:
        """Non-token-based logout: force surrender tasks and revoke user token, based on username/password auth."""
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return _error_response(
                "Access denied. Check username, password, and 'enabled' status.",
                status.HTTP_401_UNAUTHORIZED,
            )
        # note this differs from request.user which is AnonymousUser
        user = serializer.validated_data["user"]
        try:
            MarkingTaskService.surrender_all_tasks(user)
            IdentifyTaskService.surrender_all_tasks(user)
            TokenService.drop_api_token(user)
            return Response(status=status.HTTP_200_OK)
        except (ValueError, ObjectDoesNotExist, AttributeError):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
