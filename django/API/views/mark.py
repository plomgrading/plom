# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status

from Papers.services import SpecificationService


class QuestionMaxMark_how_to_get_data(APIView):
    """
    Return the max mark for a given question.

    TODO: how do I make the `data["q"]` thing work?  This always fails with KeyError
    """

    def get(self, request):
        data = request.query_params
        try:
            question = int(data["q"])
            version = int(data["v"])
        except KeyError:
            exc = APIException()
            exc.status_code = status.HTTP_400_BAD_REQUEST
            exc.detail = "Missing question and/or version data."
            raise exc
        except (ValueError, TypeError):
            exc = APIException()
            exc.status_code = status.HTTP_400_BAD_REQUEST
            exc.detail = "question and version must be integers"
            raise exc
        spec = SpecificationService()
        return Response(spec.get_question_mark(question))


class QuestionMaxMark(APIView):
    """
    Return the max mark for a given question.

    Returns:
        (200): returns the maximum number of points for a question
        (400): malformed, missing question, etc, TODO: not implemented
        (416): question values out of range
    """

    def get(self, request, *, question):
        spec = SpecificationService()
        try:
            return Response(spec.get_question_mark(question))
        except KeyError:
            exc = APIException()
            exc.status_code = status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
            exc.detail = "question out of range"
            raise exc
