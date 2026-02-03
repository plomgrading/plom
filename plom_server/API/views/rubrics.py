# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2026 Colin B. Macdonald
# Copyright (C) 2024-2025 Bryan Tanady
# Copyright (C) 2024 Aden Chan

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status, serializers

from plom.plom_exceptions import PlomConflict
from plom_server.Rubrics.services import RubricService
from plom_server.Mark.serializers.tasks import MarkingTaskSerializer

from plom_server.UserManagement.models import User

from .utils import _error_response


class MgetAllRubrics(APIView):
    def get(self, request: Request) -> Response:
        all_rubric_data = RubricService.get_rubrics_as_dicts()
        if not all_rubric_data:
            return _error_response(
                "Server has no rubrics: check server settings",
                status.HTTP_404_NOT_FOUND,
            )
        return Response(all_rubric_data, status=status.HTTP_200_OK)


class MgetRubricsByQuestion(APIView):
    def get(self, request: Request, *, question: int) -> Response:
        all_rubric_data = RubricService.get_rubrics_as_dicts(question_idx=question)
        if not all_rubric_data:
            return _error_response(
                "Server has no rubrics: check server settings",
                status.HTTP_404_NOT_FOUND,
            )
        return Response(all_rubric_data, status=status.HTTP_200_OK)


# GET: /MK/user/{username}/{question}
# PUT: /MK/user/{username}/{question}


class MgetRubricPanes(APIView):
    def get(self, request: Request, *, username: str, question: int) -> Response:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return _error_response(
                f"User {username} doesn't exist",
                status.HTTP_400_BAD_REQUEST,
            )
        pane = RubricService.get_rubric_pane(user, question)
        return Response(pane, status=status.HTTP_200_OK)

    def put(self, request: Request, *, username: str, question: int) -> Response:
        rs = RubricService()
        config = request.data["rubric_config"]
        rs.update_rubric_pane(request.user, question, config)
        return Response(status=status.HTTP_200_OK)


# PUT: /MK/rubric
class McreateRubric(APIView):
    """Create a new rubric on the server."""

    def put(self, request: Request) -> Response:
        """Create a new rubric on the server.

        Args:
            request: a request.  The data of the request should contain
                appropriate key-value pairs to define a new rubric.
                The rubric will always be created by the calling user,
                no matter what it says in the proposed rubric data.

        Returns:
            On success, responds with the JSON key-value representation
            of the new rubric.
            Responds with 406 not acceptable if the proposed data is
            invalid in some way.
            Responds with 403 if you are
            not allowed to create new rubrics.
        """
        try:
            rubric_as_dict = RubricService.create_rubric(
                request.data["rubric"], creating_user=request.user
            )
            return Response(rubric_as_dict, status=status.HTTP_200_OK)
        except (serializers.ValidationError, NotImplementedError, ValueError) as e:
            return _error_response(
                f"Invalid rubric: {e}", status.HTTP_406_NOT_ACCEPTABLE
            )
        except PermissionDenied as e:
            return _error_response(e, status.HTTP_403_FORBIDDEN)


# PATCH: /MK/rubric/{rid}
# PATCH: /MK/rubric/{rid}?minor_change
# PATCH: /MK/rubric/{rid}?major_change
# PATCH: /MK/rubric/{rid}?major_change&tag_tasks
class MmodifyRubric(APIView):
    """Change a rubric on the server."""

    def patch(self, request: Request, *, rid: int) -> Response:
        """Change a rubric on the server.

        Args:
            request: a request containing data of key-value pairs
                representing the changes you'd like to make.

        Keyword Args:
            rid: the key/id of the rubric to modify.  This is not
                the same thing as the "primary key" in the database.

        Query parameter include "major_change", "minor_change" and
        "tag_tasks" all of which are boolean (you either pass them or
        you don't).  They are used to influence what sort of revision
        this is.

        Returns:
            On success, responds with the JSON key-value representation
            of the modified rubric.
            Responds with 404 if the rubric is not found.
            Responds with 406 not acceptable if the proposed
            data is invalid in some way.  Responds with 403 if you are
            not allowed to modify this rubric.
            Responds with 409 if your modifications conflict with others'
            (e.g., two users have both modified the same rubric).

        """
        if "major_change" in request.query_params:
            if "minor_change" in request.query_params:
                return _error_response(
                    "Cannot specify both major and minor change",
                    status.HTTP_400_BAD_REQUEST,
                )
            is_minor_change = False
        elif "minor_change" in request.query_params:
            is_minor_change = True
        else:
            # TODO: default to major change: might reconsider, see also web editor default
            # is_minor_change = None
            is_minor_change = False

        if "tag_tasks" in request.query_params:
            if "no_tag_tasks" in request.query_params:
                return _error_response(
                    "Cannot specify both 'tag_tasks' and 'no_tag_tasks'",
                    status.HTTP_400_BAD_REQUEST,
                )
            tag_tasks = True
        elif "no_tag_tasks" in request.query_params:
            tag_tasks = False
        else:
            tag_tasks = None

        try:
            rubric_as_dict = RubricService.modify_rubric(
                rid,
                request.data["rubric"],
                modifying_user=request.user,
                tag_tasks=tag_tasks,
                is_minor_change=is_minor_change,
            )
            # TODO: use a serializer to get automatic conversion from Rubric object?
            return Response(rubric_as_dict, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Rubric rid={rid} not found: {e}", status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            # not catching this would work, but we don't get the full error message
            return _error_response(e, status.HTTP_403_FORBIDDEN)
        except (ValueError, serializers.ValidationError, NotImplementedError) as e:
            return _error_response(e, status.HTTP_406_NOT_ACCEPTABLE)
        except PlomConflict as e:
            return _error_response(e, status.HTTP_409_CONFLICT)


class MgetRubricMarkingTasks(APIView):
    def get(self, request: Request, *, rid: int) -> Response:
        """Returns the marking tasks associated with a rubric.

        Args:
            request: HTTP Request of the API call.

        Keyword Args:
            rid: for which rubric do we want marking tasks.

        Returns:
            On success, responds with the JSON representations of
            the tasks associated with the rubric.
            Returns 404 if the rubric is not found.

        Notes: the format of the output is still stabilizing, for example,
        the `latest_annotation` field contains a unusable URL (Issue #3521).
        TODO: Similarly, `paper` field is broken (Issue #3522).
        """
        try:
            rubric = RubricService.get_rubric_by_rid(rid)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Rubric rid={rid} not found: {e}", status.HTTP_404_NOT_FOUND
            )
        tasks = RubricService.get_marking_tasks_with_rubric_in_latest_annotation(rubric)
        serializer = MarkingTaskSerializer(
            tasks, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
