# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2024 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Natalie Balashov

from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from Identify.services import ClasslistService
from Identify.services import IdentifyTaskService, IDReaderService

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

    def delete(self, request, predictor=None):
        """Remove ID predictions from either a particular predictor or all predictors."""
        id_reader_service = IDReaderService()
        if predictor:
            try:
                id_reader_service.delete_ID_predictions(predictor)
                return Response(status=status.HTTP_200_OK)
            except RuntimeError as e:
                return _error_response(e, status.HTTP_400_BAD_REQUEST)
        else:
            for predictor_name in ("MLLAP", "MLGreedy"):
                id_reader_service.delete_ID_predictions(predictor_name)
            return Response(status=status.HTTP_200_OK)


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
        """Responds with a list of completed/total tasks."""
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
        except RuntimeError as e:
            # TODO: legacy server and client all conflate various errors to 409
            return _error_response(e, status.HTTP_409_CONFLICT)

    def put(self, request, paper_id: int) -> Response:
        """Assigns a name and a student ID to the paper.

        Raises:
            HTTP_403_FORBIDDEN: user is not the assigned user for the id-ing task for that paper
            HTTP_404_NOT_FOUND: there is no valid id-ing task for that paper
            HTTP_409_CONFLICT: the student_id has already been assigned to another paper  (not yet implemented)
        """
        data = request.data
        user = request.user
        its = IdentifyTaskService()
        try:
            its.identify_paper(user, paper_id, data["sid"], data["sname"])
        except PermissionDenied as err:  # task not assigned to that user
            return _error_response(err, status=status.HTTP_403_FORBIDDEN)
        except ObjectDoesNotExist as err:  # no valid task for that paper_id
            return _error_response(err, status=status.HTTP_404_NOT_FOUND)
        except IntegrityError as err:  # attempt to assign SID already used
            return _error_response(err, status.HTTP_409_CONFLICT)

        return Response(status=status.HTTP_200_OK)
