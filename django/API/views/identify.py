# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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


class IDgetDoneTasks(APIView):
    """When a id-client logs on they request a list of papers they have already IDd.
    Send back the list.

    TODO: Not implemented, just reports empty.
    TODO: see ``plom/db/db_identify:IDgetDoneTasks``
    """

    def get(self, request):
        return Response([])

    # TODO: how do we get the user name?
    # TODO: how do we log?


class IDgetNextTask(APIView):
    """Responds with a code for the the next available identify task.

    Note: There is no guarantee that task will still be available later but at this moment in time,
    no one else has claimed it

    Responds with status 200/204.

    TODO: Not implemented, just lies that we are done.
    TODO: see ``plom/db/db_identify:IDgetNextTask``
    """

    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class IDprogressCount(APIView):
    def get(self, request):
        return Response([42, 4897])
