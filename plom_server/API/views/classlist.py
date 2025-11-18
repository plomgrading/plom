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
from plom_server.Preparation.services import PrenameSettingService

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

    # GET /api/v0/classlist
    def get(self, request: Request) -> FileResponse | Response:
        """Fetch the classlist held by the server.

        By default, this is a transparent wrapper for the GET method
        implemented in :class:'ClasslistDownloadView'.

        Args:
            request: A Request object.

        Returns:
            A FileResponse object with filename 'classlist.csv'.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can see the class list.',
                status.HTTP_403_FORBIDDEN,
            )

        return ClasslistDownloadView().get(request)

    # Internal code shared by both POST and PATCH requests:
    def _extend(self, request: Request, startempty: bool = False) -> Response:
        """Extend the server's classlist with rows from an uploaded classlist.

        This is a thin wrapper for the method named validate_and_use_classlist_csv()
        that serves the web UI in :class:'StagingStudentService'.

        All students in the upload must be not-yet-known to the server.
        If the upload mentions even one student ID that the server
        already holds, or even a single paper number that is already in
        use, the whole operation will be cancelled.

        Args:
            request: A Request object that includes a file object.
            startempty: A flag saying whether to insist that there is
                no class list before the operation begins.

        Returns:
            A Response containing the werr chunk of the result from
            validate_and_use_classlist_csv() in its .json() attribute,
            with the HTTP status of the response determined by the
            'success' part of validate_and_use_classlist_csv().
            If 'success' is false, return status 406 with diagnostics.
            There are two short-circuit options where we don't bother
            activating the StagingStudentService. If the caller is
            outside the "manager" group, they get status 403; if they
            didn't actually send a CSV file, they get status 400.
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

        if startempty and StagingStudentService.are_there_students():
            N = StagingStudentService.how_many_students()
            return _error_response(
                f"Classlist contains {N} students; POST method expects 0.",
                status.HTTP_400_BAD_REQUEST,
            )

        classlist_csv = request.FILES["classlist_csv"]
        success, werr = StagingStudentService.validate_and_use_classlist_csv(
            classlist_csv
        )
        if not success:
            return Response(werr, status=status.HTTP_406_NOT_ACCEPTABLE)

        return Response(werr)

    # PATCH /api/v0/classlist
    def patch(self, request: Request) -> Response:
        """Extend the server's classlist with rows from an uploaded classlist.

        This is a thin wrapper for the method named validate_and_use_classlist_csv()
        that serves the web UI in :class:'StagingStudentService'.

        All students in the upload must be not-yet-known to the server.
        If the upload mentions even one student ID that the server
        already holds, or even a single paper number that is already in
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
        """Upload a new classlist to the server, requiring none yet.

        Args:
            request: A Request object that includes a file object
                identified by the key "classlist_csv".

        Returns:
            On success, the Response from the method
            validate_and_use_classlist_csv() that serves the web UI
            in :class:'StagingStudentService'.

            Attempting to POST a CSV file when the server's classlist
            is nonempty is an error, and triggers status code 400.
            (Note that the PATCH and PUT methods do not enforce this.)

            Callers outside the "manager" group get status 403
            no matter what input they provide. If there is no CSV
            file, we return status 400. If the incoming CSV file has a
            problem, we return status 406.
        """
        return self._extend(request, startempty=True)

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


class Prenaming(APIView):
    """Read or write the prenaming flag."""

    # GET /api/v0/classlist/prenaming
    def get(self, request: Request) -> Response:
        """Report the current value of the prenaming flag.

        Args:
            request: A Request object.

        Returns:
            A Response whose body text is the string "True"
            if prenaming is enabled, and "False" otherwise.
        """
        flag = PrenameSettingService().get_prenaming_setting()
        return Response(f"{flag}")

    # POST /api/v0/classlist/prenaming
    def post(self, request: Request) -> Response:
        """Set the prenaming flag.

        Args:
            request: A Request object whose POST data carries the new
                value for the prenaming setting.

        POST Data:
            newvalue: A string. If the casefold() value is "true",
                enable prenaming; for anything else, disable prenaming.

        Returns:
            An empty response, with status 204, on success.
            Callers outside the "manager" group get status 403
            no matter what input they may provide. Status 400 indicates
            that the POST data has no key "newvalue". Status 409 means
            it's too late in the process to change prenaming.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can manipulate the classlist.',
                status.HTTP_403_FORBIDDEN,
            )

        if "newvalue" not in request.POST:
            return _error_response(
                "Expected key 'newvalue' not found",
                status.HTTP_400_BAD_REQUEST,
            )

        enable = request.POST["newvalue"].casefold() == "true"
        try:
            PrenameSettingService().set_prenaming_setting(enable)
        except PlomDependencyConflict as e:
            return _error_response(
                e,
                status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
