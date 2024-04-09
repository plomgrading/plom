# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023-2024 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

from plom.plom_exceptions import PlomConflict
from Rubrics.services import RubricService

from .utils import _error_response


class MgetRubricsByQuestion(APIView):
    def get(self, request: Request, *, question: int) -> Response:
        rs = RubricService()
        all_rubric_data = rs.get_rubrics_as_dicts(question=question)
        return Response(all_rubric_data, status=status.HTTP_200_OK)


class MgetRubricPanes(APIView):
    def get(self, request: Request, username: str, question: int) -> Response:
        rs = RubricService()
        pane = rs.get_rubric_pane(request.user, question)
        return Response(pane, status=status.HTTP_200_OK)

    def put(self, request: Request, *, username: str, question: int) -> Response:
        rs = RubricService()
        config = request.data["rubric_config"]
        rs.update_rubric_pane(request.user, question, config)
        return Response(status=status.HTTP_200_OK)


class McreateRubric(APIView):
    def put(self, request: Request) -> Response:
        rs = RubricService()
        try:
            rubric = rs.create_rubric(
                request.data["rubric"], creating_user=request.user
            )
            return Response(rubric.key, status=status.HTTP_200_OK)
        except (ValidationError, NotImplementedError) as e:
            return _error_response(
                f"Invalid rubric: {e}", status.HTTP_406_NOT_ACCEPTABLE
            )


class MmodifyRubric(APIView):
    def patch(self, request: Request, *, key: str) -> Response:
        """Change a rubric on the server.

        Args:
            request: a request.

        Keyword Args:
            key: the "key" or "id" of the rubric to modify.  This is not
                guaranteed to be the "private key" in the database.  In
                fact currently it is not.

        Returns:
            On success, responds with a string, the rubric id/key.
            Responds with 404 if the rubric is not found.
            Responds with 406 not acceptable if the proposed
            data is invalid in some way.  Responds with 403 if you are
            not allowed to modify this rubric.
            Responds with 409 if your modifications conflict with others'
            (e.g., two users have both modified the same rubric).
        """
        rs = RubricService()
        try:
            rubric = rs.modify_rubric(
                key, request.data["rubric"], modifying_user=request.user
            )
            return Response(rubric.key, status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            # Django also intercepts invalid (too short) keys before we see them
            # and uses 404 for those (see the regex in ``mark_patterns.py``).
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
