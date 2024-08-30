# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

from plom.plom_exceptions import PlomConflict
from Rubrics.services import RubricService

from .utils import _error_response


class MgetAllRubrics(APIView):
    def get(self, request: Request) -> Response:
        all_rubric_data = RubricService.get_rubrics_as_dicts(question=None)
        if not all_rubric_data:
            return _error_response(
                "Server has no rubrics: check server settings",
                status.HTTP_404_NOT_FOUND,
            )
        return Response(all_rubric_data, status=status.HTTP_200_OK)


class MgetRubricsByQuestion(APIView):
    def get(self, request: Request, *, question: int) -> Response:
        all_rubric_data = RubricService.get_rubrics_as_dicts(question=question)
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


class MgetRubricUsages(APIView):
    def get(self, request: Request, *, key: int) -> Response:
        rs = RubricService()
        paper_numbers = rs.get_all_paper_numbers_using_a_rubric(key)
        return Response(paper_numbers, status=status.HTTP_200_OK)


# PUT: /MK/rubric
class McreateRubric(APIView):
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
        rs = RubricService()
        try:
            rubric_as_dict = rs.create_rubric(
                request.data["rubric"], creating_user=request.user
            )
            return Response(rubric_as_dict, status=status.HTTP_200_OK)
        except (ValidationError, NotImplementedError) as e:
            return _error_response(
                f"Invalid rubric: {e}", status.HTTP_406_NOT_ACCEPTABLE
            )
        except PermissionDenied as e:
            return _error_response(e, status.HTTP_403_FORBIDDEN)


# PATCH: /MK/rubric/{key}
class MmodifyRubric(APIView):
    def patch(self, request: Request, *, key: int) -> Response:
        """Change a rubric on the server.

        Args:
            request: a request containing data of key-value pairs
                representing the changes you'd like to make.

        Keyword Args:
            key: the "key" or "id" of the rubric to modify.  This is not
                guaranteed to be the "private key" in the database.  In
                fact currently it is not.

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
        rs = RubricService()
        try:
            rubric_as_dict = rs.modify_rubric(
                key, request.data["rubric"], modifying_user=request.user
            )
            # TODO: use a serializer to get automatic conversion from Rubric object?
            return Response(rubric_as_dict, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Rubric with key {key} not found: {e}", status.HTTP_404_NOT_FOUND
            )
        except PermissionDenied as e:
            # not catching this would work, but we don't get the full error message
            return _error_response(e, status.HTTP_403_FORBIDDEN)
        except (ValidationError, NotImplementedError) as e:
            return _error_response(e, status.HTTP_406_NOT_ACCEPTABLE)
        except PlomConflict as e:
            return _error_response(e, status.HTTP_409_CONFLICT)
