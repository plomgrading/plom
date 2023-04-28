# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import FileResponse

from Preparation.services import StagingStudentService
from Identify.services import IdentifyTaskService


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
    Get predictions for test-paper identification.

    TODO: not implemented in Django, Issue #2672.
    For now, just return all the pre-named papers.
    """

    def get(self, request, *, predictor=None):
        # TODO: Issue #2672
        assert predictor is None or predictor == "prename"
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
    """

    def get(self, request):
        its = IdentifyTaskService()
        tasks = its.get_done_tasks(request.user)

        return Response(tasks, status=status.HTTP_200_OK)

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
        its = IdentifyTaskService()
        next_task = its.get_next_task()
        if next_task:
            paper_id = next_task.paper.paper_number
            return Response(paper_id, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)


class IDprogressCount(APIView):
    def get(self, request):
        """
        Responds with a list of completed/total tasks.
        """

        its = IdentifyTaskService()
        progress = its.get_id_progress()
        return Response(progress, status=status.HTTP_200_OK)


class IDclaimThisTask(APIView):
    def patch(self, request, paper_id):
        """Claims this identifying task for the user."""

        its = IdentifyTaskService()
        try:
            its.claim_task(request.user, paper_id)
            return Response(status=status.HTTP_200_OK)
        except RuntimeError:
            return Response(
                f"ID task {paper_id} already claimed", status=status.HTTP_409_CONFLICT
            )

    def put(self, request, paper_id):
        """Assigns a name and a student ID to the paper."""

        data = request.data
        user = request.user

        its = IdentifyTaskService()
        its.identify_paper(user, paper_id, data["sid"], data["sname"])
        return Response(status=status.HTTP_200_OK)


class IDgetImage(APIView):
    def get(self, request, paper_id):
        """
        Responds with an ID page image file.
        """

        its = IdentifyTaskService()
        id_img = its.get_id_page(paper_id)

        if not id_img:
            return Response(
                f"ID page-image not found for paper {paper_id}",
                status=status.HTTP_404_NOT_FOUND,
            )

        img_path = id_img.image_file.path
        with open(img_path, "rb") as f:
            image = SimpleUploadedFile(
                f"{paper_id}_id.png",
                f.read(),
                content_type="image/png",
            )
        return FileResponse(image, status=status.HTTP_200_OK)
