# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from rest_framework.views import APIView
from rest_framework.response import Response

from Preparation.services import StagingStudentService


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
