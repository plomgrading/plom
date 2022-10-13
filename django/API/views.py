# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from Papers.services import SpecificationService
from Preparation.services import StagingStudentService
from API.models import NumberToIncrement


class InfoSpec(APIView):
    """
    Return the public part of the specification.

    Returns:
        (200) JsonResponse: the spec
        (400) spec not found
    """

    def get(self, request):
        spec = SpecificationService()
        if not spec.is_there_a_spec():
            exc = APIException()
            exc.status_code = status.HTTP_400_BAD_REQUEST
            exc.detail = "Server does not have a spec."
            raise exc

        the_spec = spec.get_the_spec()
        the_spec.pop("privateSeed", None)
        the_spec.pop("publicCode", None)

        return Response(the_spec)


class QuestionMaxMark(APIView):
    """
    Return the max mark for a given question.
    """

    def get(self, request):
        data = request.query_params
        question = int(data["q"])
        version = int(data["v"])

        spec = SpecificationService()
        return Response(spec.get_question_mark(question))


class NumberIncrement(APIView):
    """
    The user can view or increment a number.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_number, created = NumberToIncrement.objects.get_or_create(user=user)
        response_dict = {"number": user_number.number, "created": created}
        return Response(response_dict)

    def post(self, request):
        user = request.user
        user_number, created = NumberToIncrement.objects.get_or_create(user=user)
        user_number.number += 1
        user_number.save()
        response_dict = {"number": user_number.number, "created": created}
        return Response(response_dict)


class ServerVersion(APIView):
    """
    Get the server version. (Debug: hardcoded for now)
    """

    def get(self, request):
        version = "Plom server version 0.12.0.dev with API 55"
        return Response(version)


class GetClasslist(APIView):
    """
    Get the classlist.
    """

    def get(self, request):
        sstu = StagingStudentService()
        if sstu.are_there_students():
            students = sstu.get_students()
            
            # TODO: new StudentService or ClasslistService that implements
            # the loop below?
            for s in students:
                s["id"] = s.pop("student_id")
                s["name"] = s.pop("student_name")

            return Response(students)


class GetIDPredictions(APIView):
    """
    Get predictions for test-paper identification. TODO: not implemented in Django
    For now, just return all the pre-named papers
    """

    def get(self, request):
        sstu = StagingStudentService()
        if sstu.are_there_students():
            predictions = {}
            for s in sstu.get_students():
                if s["paper_number"]:
                    predictions[s["paper_number"]] = {
                        "student_id": s["student_id"],
                        "certainty": 100,
                        "predictor": "preID",
                    }
            return Response(predictions)
