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

        Args:
            request: A Request object that gets ignored.

        Returns:
            (200) FileResponse
        """
        zzz = ClasslistDownloadView().get(request)
        print(f"In ClasslistHandler.get(), type(zzz) = {type(zzz)}.")
        return zzz
