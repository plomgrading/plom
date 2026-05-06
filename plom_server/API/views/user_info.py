# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Bryan Tanady
# Copyright (C) 2026 Aidan Murphy
# Copyright (C) 2026 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status

from plom_server.UserManagement.services import UsersService
from plom_server.Authentication.services import AuthService

from .utils import _error_response


class UsersInfo(APIView):
    """Information about users on the system."""

    # GET /info/users/
    def get(self, request: Request) -> Response:
        """Get a list of users, their usernames, uid, what groups they belong to and other info.

        Responses:
            200 when it succeeds, returning list of dicts, each with at least keys
            for "username", "uid", "name", and "groups".
        """
        response_list = UsersService.get_user_info_list_of_dicts()
        return Response(response_list, status=status.HTTP_200_OK)


class UserManage(APIView):
    """API to manage user accounts."""

    # POST /api/beta/users/<username>
    def post(self, request: Request, *, username) -> Response:
        """Generate a password reset link for the specified user.

        Responses:
            200 when it succeeds, returning a username and password reset link.
            400 for invalid username.
            403 if you do not have permissions to generate a password reset link.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only "manager" users can generate password reset links',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            password_reset_link_dict = AuthService().generate_password_reset_links_dict(
                request, [username]
            )
            password_reset_link = password_reset_link_dict[username]
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Invalid username supplied: {e}",
                status.HTTP_400_BAD_REQUEST,
            )

        response_dict = {
            "username": username,
            "password_reset_link": password_reset_link,
        }
        return Response(response_dict, status=status.HTTP_200_OK)

    # PUT /api/beta/users/<username>?group=<group1>&group=<group2>
    def put(self, request: Request, *, username: str) -> Response:
        """Create a user account belonging to a number of groups.

        You must pass at least one "group=" in each request.

        Responses:
            200 when it succeeds, returning the username, groups and a
                password reset link for the created user.
            400 for invalid username or user groups.
            403 if you do not have permissions to create users.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only "manager" users can create users',
                status.HTTP_403_FORBIDDEN,
            )

        groups = request.query_params.getlist("group")
        if not groups:
            return _error_response(
                'You must provide at least one "group=" query parameter',
                status.HTTP_400_BAD_REQUEST,
            )
        try:
            created_username, joined_groups = AuthService.create_user_and_add_to_groups(
                username, groups
            )
        except (ObjectDoesNotExist, ValueError, IntegrityError) as e:
            return _error_response(
                f"Couldn't create user, {e}",
                status.HTTP_400_BAD_REQUEST,
            )

        password_reset_link_dict = AuthService().generate_password_reset_links_dict(
            request, [created_username]
        )
        password_reset_link = password_reset_link_dict[created_username]

        response_dict = {
            "username": created_username,
            "groups": joined_groups,
            "password_reset_link": password_reset_link,
        }
        return Response(response_dict, status=status.HTTP_200_OK)
