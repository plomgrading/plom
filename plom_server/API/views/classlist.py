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


class Classlist(APIView):
    """Handle transactions involving the classlist held by the server."""

    # DELETE /api/v0/classlist
    def delete(self, request: Request) -> Response:
        """Delete the classlist held by the server.

        Args:
            request: A Request object.

        Returns:
            Empty response with code 204 on success. Error return codes
            could be 403 for a user outside the 'manager' group, or
            409 if manipulating the classlist is forbidden for another reason.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can delete the class list.',
                status.HTTP_403_FORBIDDEN,
            )
        try:
            StagingStudentService.remove_all_students()
        except PlomDependencyConflict as e:
            return _error_response(
                f"Manipulating the classlist is not allowed. {e}",
                status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _werr_to_http(self, werr: tuple) -> Response:
        """Build a proper HTTP response from a werr tuple.

        Args:
            werr: A 2-tuple (s,l), where ...
                s is the boolean value of the statement "The operation succeeded",
                l is a list of dicts describing warnings, errors, or notes.
                This thing originates mostly in Vlad, the classlist validator,
                where further details may be found.

        Returns:
            A Response object whose status code and text value are
            determined by the contents of the given werr tuple.
            In the case of success with notes, the notes are returned
            as a string and the status is 200; if the operation succeeded
            and there are no notes, return no content with status 204.
            If the success flag is False, return the notes with status 400.
        """
        notes = werr[1]
        if not werr[0]:
            # Something failed; presumably details are available.
            return _error_response(
                f"{notes}",
                status.HTTP_400_BAD_REQUEST,
            )

        if len(notes) > 0:
            return Response(f"{notes}")

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
        already holds, or even a single test number that is already in
        use, the whole operation will be cancelled.

        Args:
            request: A Request object that includes a file object.

        Returns:
            The Response from the method cited above, except for two
            short-circuit options where we don't bother activating the
            StagingStudentService. If the caller is outside the "manager"
            group, they get status 403; if they didn't actually send a
            classlist, they get status 400.
        """
        # The service we will call has weak defences against faulty inputs.
        # Check here that the requested action should be allowed.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can delete the class list.',
                status.HTTP_403_FORBIDDEN,
            )

        if not request.FILES["classlist_csv"]:
            return _error_response(
                "No classlist provided.",
                status.HTTP_400_BAD_REQUEST,
            )

        classlist_csv = request.FILES["classlist_csv"]

        return self._werr_to_http(
            StagingStudentService.validate_and_use_classlist_csv(classlist_csv)
        )

    # PATCH /api/v0/classlist
    def patch(self, request: Request) -> Response:
        """Extend the server's classlist with rows from an uploaded classlist.

        This is a thin wrapper for the method named validate_and_use_classlist_csv()
        that serves the web UI in :class:'StagingStudentService'.

        All students in the upload must be not-yet-known to the server.
        If the upload mentions even one student ID that the server
        already holds, or even a single test number that is already in
        use, the whole operation will be cancelled.

        Args:
            request: A Request object that includes a file object.

        Returns:
            The Response from the method cited above, except for two
            short-circuit options where we don't bother activating the
            StagingStudentService. If the caller is outside the "manager"
            group, they get status 403; if they didn't actually send a
            classlist, they get status 400.
        """
        # Yes, the docstring above is identical to the one for _extend().
        # The 1-line method body below explains why that is appropriate.
        return self._extend(request)

    # POST /api/v0/classlist
    def post(self, request: Request) -> Response:
        """Upload a new classlist to the server, insisting that it starts empty.

        Args:
            request: A Request object that includes a file object
                identified by the key "classlist_csv"

        Returns:
            The Response from the method validate_and_use_classlist_csv()
            that serves the web UI in :class:'StagingStudentService',
            outside the following special cases. If the caller is outside
            the "manager" group, they get status 403; if they didn't actually
            send a classlist, they get status 400.
        """
        if StagingStudentService.are_there_students():
            N = StagingStudentService.how_many_students()
            return _error_response(
                f"Classlist contains {N} students; POST method expects 0.",
                status.HTTP_400_BAD_REQUEST,
            )
        return self._extend(request)

    # PUT /api/v0/classlist
    def put(self, request: Request) -> Response:
        """Upload a new classlist to the server, replacing whatever is there.

        Args:
            request: A Request object that includes a file object
                identified by the key "classlist_csv"

        Returns:
            The Response from the method validate_and_use_classlist_csv()
            that serves the web UI in :class:'StagingStudentService',
            outside the following special cases. If the caller is outside
            the "manager" group, they get status 403; if they didn't actually
            send a classlist, they get status 400.
        """
        self.delete(request)
        return self._extend(request)
