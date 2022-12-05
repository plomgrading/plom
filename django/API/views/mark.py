# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework import status

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import FileResponse

from Papers.services import SpecificationService
from Papers.models import Paper, Image

from Mark.services import MarkingTaskService, PageDataService


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
        mss = MarkingTaskService()
        the_task = mss.get_task_from_code(code)
        mss.assign_task_to_user(request.user, the_task)

        pds = PageDataService()
        paper, question = mss.unpack_code(code)
        question_data = pds.get_question_pages_list(paper, question)

        # TODO: tags and integrity check are hardcoded for now
        return Response([question_data, [], "12345"])


class MgetQuestionPageData(APIView):
    """
    Get page metadata for a particular test-paper and question.
    """

    def get(self, request, paper, question, *args):
        pds = PageDataService()

        try:
            page_metadata = pds.get_question_pages_metadata(paper, question)
            return Response(page_metadata, status=status.HTTP_200_OK)
        except Paper.DoesNotExist:
            raise APIException(
                detail="Test paper does not exist.", status=status.HTTP_400_BAD_REQUEST
            )


class MgetOneImage(APIView):
    """
    Get a page image from the server.
    """

    def get(self, request, pk, hash):
        pds = PageDataService()

        try:
            img_path = pds.get_image_path(pk, hash)
            with open(img_path, "rb") as f:
                image = SimpleUploadedFile(
                    f"{hash}.png",
                    f.read(),
                    content_type="image/png",
                )
            return FileResponse(image, status=status.HTTP_200_OK)
        except Image.DoesNotExist:
            raise APIException(
                detail="Image does not exist.",
                status=status.HTTP_400_BAD_REQUEST,
            )


class MgetAnnotations(APIView):
    """
    Get the latest annotations for a question.
    """

    def get(self, request, paper, question):
        return Response({"annotation_edition": None}, status=status.HTTP_200_OK)


class MgetAnnotationImage(APIView):
    """
    Get an annotation-image.
    """

    def get(self, request, paper, question):
        return Response({}, status=status.HTTP_200_OK)