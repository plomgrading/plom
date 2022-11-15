# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status

from Papers.services import SpecificationService


class QuestionMaxMark(APIView):
    """
    Return the max mark for a given question.

    TODO: is there a decorator for required data fields?

    Returns:
        (200):
        (400): malformed, missing question, etc
        (416): question/version values out of range
            (Not implemented yet)
    """

    def get(self, request):
        print(request)
        data = request.query_params
        print(data)
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
        # if question < 1 or question > self.server.testSpec["numberOfQuestions"]:
        #     raise web.HTTPRequestRangeNotSatisfiable(
        #         reason="Question out of range - please check and try again.",
        #     )
        # if version < 1 or version > self.server.testSpec["numberOfVersions"]:
        #     raise web.HTTPRequestRangeNotSatisfiable(
        #         reason="Version out of range - please check and try again.",
        #     )

        spec = SpecificationService()
        return Response(spec.get_question_mark(question))


class QuestionMaxMark2(APIView):
    """
    Return the max mark for a given question.

    Returns:
        (200):
        (400): malformed, missing question, etc, TODO: not implemented
        (416): question values out of range
    """

    def get(self, request, *, question):
        print(request)
        data = request.query_params
        print(data)
        print(question)
        print(type(question))
        spec = SpecificationService()
        try:
            return Response(spec.get_question_mark(question))
        except KeyError:
            exc = APIException()
            exc.status_code = status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
            exc.detail = "question out of range"
            raise exc
