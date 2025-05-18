# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

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
            request: A Request object that gets ignored.

        Returns:
            (200) Response with nothing but confirming text.
            (409) Manipulating the classlist is not allowed.
        """
        SSS = StagingStudentService()
        try:
            SSS.remove_all_students()
        except PlomDependencyConflict as e:
            return _error_response(
                f"Manipulating the classlist is not allowed. {e}",
                status.HTTP_409_CONFLICT,
            )

        return Response("OK, classlist deleted.")

    # GET /api/v0/classlist
    def get(self, request: Request) -> FileResponse:
        """Fetch the classlist held by the server.

        This is a transparent wrapper for the GET method
        implemented in :class:'ClasslistDownloadView'.

        Args:
            request: A Request object that gets ignored.

        Returns:
            (200) FileResponse
        """
        return ClasslistDownloadView().get(request)

    # POST /api/v0/classlist
    def post(self, request: Request) -> Response:
        """Extend classlist on server with rows from an uploaded classlist.

        This is a transparent wrapper for the POST method
        implemented to serve the web UI in :class:'StagingStudentService'.

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
        """
        # Here we want a thin wrapper around plom_server/Preparation/views/...
        # But that code has no error-defence. So put it there, not here!

        if not request.FILES["classlist_csv"]:
            success = False
            werr = [{"errors": "No classlist provided."}]
            return (success, werr)

        classlist_csv = request.FILES["classlist_csv"]

        SSS = StagingStudentService()
        zzz = SSS.validate_and_use_classlist_csv(classlist_csv)
        return Response(zzz)
