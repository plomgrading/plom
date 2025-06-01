# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from typing import Dict, List, Union

from django.http import FileResponse

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status

from plom.plom_exceptions import PlomDependencyConflict
from plom_server.Preparation.services import StagingStudentService
from plom_server.Preparation.views import ClasslistDownloadView

# from .utils import debugnote
from .utils import _error_response


class ClasslistHandler(APIView):
    """Handle transactions involving the classlist held by the server."""

    # DELETE /api/v0/classlist
    def delete(self, request: Request) -> Response:
        """Delete the classlist held by the server.

        Args:
            request: A Request object.

        Returns:
            Empty response with code 204 on success. Error return codes
            could be 401 for a user outside the 'manager' group, or
            409 if manipulating the classlist is forbidden for another reason.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can delete the class list.',
                status.HTTP_401_FORBIDDEN,
            )
        try:
            StagingStudentService.remove_all_students()
        except PlomDependencyConflict as e:
            return _error_response(
                f"Manipulating the classlist is not allowed. {e}",
                status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    # GET /api/v0/classlist
    def get(self, request: Request) -> FileResponse:
        """Fetch the classlist held by the server.

        This is a transparent wrapper for the GET method
        implemented in :class:'ClasslistDownloadView'.

        Args:
            request: A Request object.

        Returns:
            A FileResponse object (subclassed from Response) with filename
            'classlist.csv', and status code 200.
        """
        return ClasslistDownloadView().get(request)

    # Internal code shared by both POST and PATCH requests:
    def _extend(self, request: Request) -> Response:
        """Extend the server's classlist with rows from an uploaded classlist.

        This is a thin wrapper for the method named validate_and_use_classlist_csv()
        that serves the web UI in :class:'StagingStudentService'.

        All students in the upload must be not-yet-known to the server.
        If the upload mentions even one student ID that the server
        already holds, the whole operation will be cancelled.

        Args:
            request: A Request object that includes a file object.

        Returns:
            A Response with status code 200 containing a 2-tuple (s,l), where
            s is the boolean value of the statement "The operation succeeded",
            l is a list of dicts describing warnings, errors, or notes.

            When s==False, the classlist in the database remains unchanged.

        Raises:
            PlomDependencyConflict: If dependencies not met.
        """
        werr: List[Dict[str, Union[int, str, None]]] = []
        # The service we will call has weak defences against faulty inputs.
        # Check here that the requested action should be allowed.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            success = False
            werr.append(
                {
                    "warn_or_err": "error",
                    "werr_line": None,
                    "werr_text": "Only users in the 'manager' group can manipulate the classlist.",
                }
            )
            return Response((success, werr))

        if not request.FILES["classlist_csv"]:
            success = False
            werr.append(
                {
                    "warn_or_err": "error",
                    "werr_line": None,
                    "werr_text": "No classlist provided.",
                }
            )
            return Response((success, werr))

        classlist_csv = request.FILES["classlist_csv"]

        return Response(
            StagingStudentService.validate_and_use_classlist_csv(classlist_csv)
        )

    # PATCH /api/v0/classlist
    def patch(self, request: Request) -> Response:
        """Extend the server's classlist with info in an attached upload.

        Args:
            request: A Request object that includes a file object
                identified by the key "classlist_csv"

        Returns:
            A Response with status code 200 containing a 2-tuple (s,l), where
            s is the boolean value of the statement "The operation succeeded",
            l is a list of dicts describing warnings, errors, or notes.

            When s==False, the classlist in the database remains unchanged.

        Raises:
            PlomDependencyConflict: If dependencies not met.
        """
        return self._extend(request)

    # POST /api/v0/classlist
    def post(self, request: Request) -> Response:
        """Upload a new classlist to the server, assuming it has none.

        Args:
            request: A Request object that includes a file object
                identified by the key "classlist_csv"

        Returns:
            A Response with status code 200 containing a 2-tuple (s,l), where
            s is the boolean value of the statement "The operation succeeded",
            l is a list of dicts describing warnings, errors, or notes.

            When s==False, the classlist in the database remains unchanged.

        Raises:
            PlomDependencyConflict: If dependencies not met.
        """
        werr: List[Dict[str, Union[int, str, None]]] = []
        if StagingStudentService.are_there_students():
            success = False
            N = StagingStudentService.how_many_students()
            werr.append(
                {
                    "warn_or_err": "error",
                    "werr_line": None,
                    "werr_text": f"Classlist contains {N} students; POST method expects 0.",
                }
            )
            return Response((success, werr))
        return self._extend(request)

    # PUT /api/v0/classlist
    def put(self, request: Request) -> Response:
        """Upload a new classlist to the server, replacing whatever is there.

        Args:
            request: A Request object that includes a file object
                identified by the key "classlist_csv"

        Returns:
            A Response with status code 200 containing a 2-tuple (s,l), where
            s is the boolean value of the statement "The operation succeeded",
            l is a list of dicts describing warnings, errors, or notes.

            When s==False, the classlist in the database remains unchanged.

        Raises:
            PlomDependencyConflict: If dependencies not met.
        """
        self.delete(request)
        return self._extend(request)
