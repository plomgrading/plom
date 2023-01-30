# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import APIException, ValidationError
from rest_framework import status

from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import FileResponse

from Papers.services import SpecificationService
from Papers.models import Paper, Image

from Mark.services import MarkingTaskService, PageDataService
from Mark.models import AnnotationImage, MarkingTask


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


class MarkingProgressCount(APIView):
    """Responds with a list of completed/total tasks.

    Returns:
        (200): returns two integers, first the number of marked papers
            for this question/version and the total number of papers for
            this question/version.
        (400): malformed such as non-integers for question/version.
        (416): question values out of range: NOT IMPLEMENTED YET.
            (In legacy, this was thrown by the backend).
    """

    def get(self, request):
        data = request.data
        try:
            question = int(data["q"])
            version = int(data["v"])
        except (ValueError, TypeError):
            exc = APIException()
            exc.status_code = status.HTTP_400_BAD_REQUEST
            exc.detail = "question and version must be integers"
            raise exc
        mts = MarkingTaskService()
        progress = mts.get_marking_progress(question, version)
        return Response(progress, status=status.HTTP_200_OK)


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
        return Response(task.code)


class MclaimThisTask(APIView):
    def patch(self, request, code, *args):
        """
        Attach a user to a marking task and return the task's metadata.
        """

        mss = MarkingTaskService()
        the_task = mss.get_task_from_code(code)
        mss.assign_task_to_user(request.user, the_task)

        pds = PageDataService()
        paper, question = mss.unpack_code(code)
        question_data = pds.get_question_pages_list(paper, question)

        # TODO: tags and integrity check are hardcoded for now
        return Response([question_data, [], "12345"])

    def post(self, request, code, *args):
        """
        Accept a marker's grade and annotation for a task.
        """

        mts = MarkingTaskService()
        data = request.POST
        files = request.FILES

        plomfile = request.FILES["plomfile"]
        plomfile_data = plomfile.read().decode("utf-8")

        try:
            mark_data, annot_data = mts.validate_and_clean_marking_data(
                request.user, code, data, plomfile_data
            )
        except ObjectDoesNotExist as e:
            raise APIException(e, code=status.HTTP_404_NOT_FOUND)
        except RuntimeError as e:
            raise APIException(e, code=status.HTTP_409_CONFLICT)
        except ValidationError as e:
            raise APIException(e, code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        annotation_image = files["annotation_image"]
        try:
            img_md5sum = data["md5sum"]
            img = mts.save_annotation_image(img_md5sum, annotation_image)
        except FileExistsError:
            raise APIException(
                "Annotation image already exists.", code=status.HTTP_409_CONFLICT
            )
        except ValidationError:
            raise APIException(
                "Unsupported media type for annotation image",
                code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        mts.mark_task(request.user, code, mark_data["score"], img, annot_data)

        return Response(
            [mts.get_n_marked_tasks(), mts.get_n_total_tasks()],
            status=status.HTTP_200_OK,
        )


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
