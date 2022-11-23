# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status
from django.contrib.auth.models import User

from Papers.services import SpecificationService
from Mark.services import MarkingTaskService


class QuestionMaxMark_how_to_get_data(APIView):
    """
    Return the max mark for a given question.

    TODO: how do I make the `data["q"]` thing work?  This always fails with KeyError
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


class MgetNextTask(APIView):
    """
    Responds with a code for the next available marking task.
    """

    def get(self, request, *args):
        data = request.data
        question = data["q"]
        version = data["v"]

        # return Response("q0001g1")
        # TODO: find another place for populating the marking tasks table
        mts = MarkingTaskService()
        if not mts.are_there_tasks():
            mts.init_all_tasks()

        task = mts.get_first_available_task(question=question, version=version)
        print(task.code)
        return Response(task.code)


class MclaimThisTask(APIView):
    """
    Attach a user to a marking task and return the task's metadata.
    """

    def patch(self, request, code, *args):
        print(request.data)

        mss = MarkingTaskService()
        the_task = mss.get_task_from_code(code)

        # TODO: We should get the user from request.user
        # which requires more work w.r.t. DRF's TokenAuthentication framework
        username = request.data["user"]
        the_user = User.objects.get(username=username)
        mss.assign_task_to_user(the_user, the_task)

        # TODO: annotations and tags aren't implemented yet.
        # Thus, the null response
        return Response([[], [], []])
