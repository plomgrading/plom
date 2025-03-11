# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Aden Chan

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status, serializers

from plom.plom_exceptions import PlomConflict
from Rubrics.services import RubricService
from Mark.serializers.tasks import MarkingTaskSerializer

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


class MgetRubricPanes(APIView):
    def get(self, request: Request, *, username: str, question: int) -> Response:
        rs = RubricService()
        pane = rs.get_rubric_pane(request.user, question)
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

        Returns:
            On success, responds with the JSON key-value representation
            of the new rubric.
            Responds with 406 not acceptable if the proposed data is
            invalid in some way.
            Responds with 403 if you are
            not allowed to create new rubrics.
        """
        try:
            rubric_as_dict = RubricService().create_rubric(
                request.data["rubric"], creating_user=request.user
            )
            return Response(rubric_as_dict, status=status.HTTP_200_OK)
        except (serializers.ValidationError, NotImplementedError) as e:
            return _error_response(
                f"Invalid rubric: {e}", status.HTTP_406_NOT_ACCEPTABLE
            )
        except PermissionDenied as e:
            return _error_response(e, status.HTTP_403_FORBIDDEN)


# PATCH: /MK/rubric/{rid}
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
        try:
            rubric_as_dict = RubricService().modify_rubric(
                rid,
                request.data["rubric"],
                modifying_user=request.user,
                tag_tasks=False,
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
        except (serializers.ValidationError, NotImplementedError) as e:
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
        rs = RubricService()

        try:
            rubric = rs.get_rubric_by_rid(rid)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Rubric rid={rid} not found: {e}", status.HTTP_404_NOT_FOUND
            )
        tasks = rs.get_marking_tasks_with_rubric_in_latest_annotation(rubric)
        serializer = MarkingTaskSerializer(
            tasks, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
