# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2026 Colin B. Macdonald
# Copyright (C) 2023-2025 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from plom.plom_exceptions import PlomConflict
from plom_server.Identify.services import ClasslistService
from plom_server.Identify.services import (
    IDDirectService,
    IdentifyTaskService,
    IDProgressService,
    IDReaderService,
)

from .utils import _error_response


class GetClasslist(APIView):
    """Get the classlist."""

    def get(self, request: Request) -> Response:
        students = ClasslistService.get_students_in_api_format()
        return Response(students)


class GetIDPredictions(APIView):
    """Get, put and delete predictions for test-paper identification.

    If no predictor is specified, get or delete all predictions.

    Client needs predictions to be formatted as a dict of lists,
    where each list contains an inner dict with prediction
    info for a particular predictor (could have more than one).
    """

    def get(self, request, *, predictor=None):
        """Get ID predictions from either a particular predictor or all predictors.

        Returns:
            dict: a dict keyed by paper_number of lists of prediction dicts
            if returning all ID predictions, or a dict of dicts if returning
            only predictions for a single predictor.
        """
        id_reader_service = IDReaderService()
        if not predictor:
            predictions = id_reader_service.get_ID_predictions()
        else:
            predictions = id_reader_service.get_ID_predictions(predictor=predictor)
        return Response(predictions)

    def put(self, request):
        """Add or change ID predictions."""
        data = request.data
        user = request.user
        id_reader_service = IDReaderService()
        for paper_num in data:
            id_reader_service.add_or_change_ID_prediction(
                user,
                int(paper_num),
                data[paper_num]["student_id"],
                data[paper_num]["certainty"],
                data[paper_num]["predictor"],
            )
        return Response(status=status.HTTP_200_OK)

    def delete(self, request: Request, *, predictor: str | None = None) -> Response:
        """Remove ID predictions from either a particular predictor or all ML predictors."""
        if predictor:
            try:
                IDReaderService.delete_ID_predictions(predictor)
            except RuntimeError as e:
                return _error_response(e, status.HTTP_400_BAD_REQUEST)
            return Response(status=status.HTTP_200_OK)

        IDReaderService.delete_all_ML_ID_predictions()
        return Response(status=status.HTTP_200_OK)


# GET: /ID/tasks/complete
class IDgetDoneTasks(APIView):
    """Send back a list of papers a user has already IDd."""

    def get(self, request):
        """Get a list of papers a user has already IDd."""
        tasks = IdentifyTaskService.get_done_tasks(request.user)
        return Response(tasks, status=status.HTTP_200_OK)


# GET: /ID/tasks/available
class IDgetNextTask(APIView):
    """Used to ask for code of the next available task."""

    def get(self, request):
        """Responds with a code for the next available identify task.

        Note: There is no guarantee that task will still be available
        later but at this moment in time, no one else has claimed it.
        Its also possible you don't have permissions to actually ID
        the task; this method just tells you the task is available.

        Responds with status 200/204.
        """
        next_task = IdentifyTaskService.get_next_task()
        if next_task:
            paper_id = next_task.paper.paper_number
            return Response(paper_id, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)


class IDprogressCount(APIView):
    """Get lists of completed/total tasks."""

    def get(self, request):
        """Responds with a list of completed/total tasks."""
        progress = IdentifyTaskService.get_id_progress()
        return Response(progress, status=status.HTTP_200_OK)


# PATCH: /ID/tasks/{paper_num}
# PUT: /ID/tasks/{paper_num}
class IDclaimOrSubmitTask(APIView):
    """Claim or submit IDing tasks."""

    def patch(self, request: Request, *, paper_num: int) -> Response:
        """Claims this identifying task for the user.

        Raises:
            HTTP_403_FORBIDDEN: user is not allowed to identify papers.
            HTTP_404_NOT_FOUND: there is no valid id-ing task for that paper.
            HTTP_409_CONFLICT: task already taken.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "identifier" not in group_list:
            return _error_response(
                'Only "identifier" users can claim ID tasks',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            IdentifyTaskService.claim_task(request.user, paper_num)
            return Response(status=status.HTTP_200_OK)
        except ObjectDoesNotExist as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except PlomConflict as e:
            return _error_response(e, status.HTTP_409_CONFLICT)

    def put(self, request: Request, *, paper_num: int) -> Response:
        """Assigns a name and a student ID to the paper.

        Raises:
            HTTP_403_FORBIDDEN: user is not the assigned user for the
                ID-ing task for that paper, or the user is not in the
                "identifier" group.
            HTTP_404_NOT_FOUND: there is no valid id-ing task for that paper
            HTTP_409_CONFLICT: the student_id has already been assigned to another paper  (not yet implemented)
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "identifier" not in group_list:
            return _error_response(
                'Only "identifier" users can assign IDs',
                status.HTTP_403_FORBIDDEN,
            )
        data = request.data
        user = request.user
        try:
            IdentifyTaskService.identify_paper(
                user, paper_num, data["sid"], data["sname"]
            )
        except PermissionDenied as err:  # task not assigned to that user
            return _error_response(err, status=status.HTTP_403_FORBIDDEN)
        except ObjectDoesNotExist as err:  # no valid task for that paper_num
            return _error_response(err, status=status.HTTP_404_NOT_FOUND)
        except IntegrityError as err:  # attempt to assign SID already used
            return _error_response(err, status.HTTP_409_CONFLICT)

        return Response(status=status.HTTP_200_OK)


class IDdirect(APIView):
    """These are "beta" endpoints for "directly" identifying papers, bypassing "task" mechanisms."""

    # PUT: /ID/beta/{papernum}&student_id=...
    def put(self, request: Request, *, papernum: int) -> Response:
        """Put a particular student id in place as the identity of a paper.

        You must pass both `sid=` and `sname=` in query parameters.

        Responses:
            200 when it succeeds, currently with no content.
            400 for invalid name / sid.
            403 if you do not have permissions to ID papers.
            404 for no such paper.
            409 if that student id is in-use for another paper.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "identifier" not in group_list:
            return _error_response(
                'Only "identifier" users can ID papers',
                status.HTTP_403_FORBIDDEN,
            )

        student_id = request.query_params.get("student_id")
        student_name = request.query_params.get("student_name")
        if not student_id:
            return _error_response(
                'You must provide a "student_id=" query parameter',
                status.HTTP_400_BAD_REQUEST,
            )
        if not student_name:
            return _error_response(
                'You must provide a "student_name=" query parameter',
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            # TODO: papernum and paper_id same?
            IDDirectService.identify_direct(
                request.user, papernum, student_id, student_name
            )
            return Response(status=status.HTTP_200_OK)
        except ValueError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        except IntegrityError as e:
            return _error_response(e, status.HTTP_409_CONFLICT)
        except RuntimeError as e:
            # thought to be impossible, but if it happens its a conflict
            return _error_response(e, status.HTTP_409_CONFLICT)

    # DELETE: /ID/beta/{papernum}
    def delete(self, request: Request, *, papernum: int) -> Response:
        """Unidenfies a paper number.

        Response:
            200: success.
            403: no permission.
            404: no paper.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "identifier" not in group_list:
            return _error_response(
                'Only "identifier" users can ID papers',
                status.HTTP_403_FORBIDDEN,
            )
        try:
            IDProgressService().clear_id_from_paper(papernum)
        except ValueError as e:
            return _error_response(e, status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_200_OK)
