# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status

from plom.plom_exceptions import PlomDependencyConflict
from plom_server.Preparation.services import (
    PQVMappingService,
    StagingStudentService,
)
from plom_server.Papers.services import (
    PaperCreatorService,
    PaperInfoService,
)
from .utils import _error_response


class PQVmap(APIView):
    """Handle API requests to manipulate the PQV map."""

    # DELETE /api/beta/pqvmap
    def delete(self, request: Request) -> Response:
        """Remove the current PQV map, if any, from the database.

        This work is done by Huey, taking a blocking foreground approach.

        The response will be generated only after all the deletions are
        complete. For large classes, this may take so long that the
        requester gives up and declares an HTTP timeout. This has not yet
        been observed in the wild, but we note it here in case some
        unfortunate colleague in the future needs a pointer on what's breaking.

        Args:
            request: An HTTP request.

        Returns:
            An empty response with status 204, on success.
            Status 403 if the caller is not in the 'manager' group;
            status 409 if there is some other kind of conflict.
        """
        # Reject the request if the user is not in the 'manager' group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can clean the database.',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            PaperCreatorService.remove_all_papers_from_db(background=False)
        except PlomDependencyConflict as err:
            return _error_response(
                f"Dependency Conflict. The database cannot be cleared right now. {err}",
                status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    # GET /api/beta/pqvmap
    def get(self, request: Request) -> Response:
        """Get the current PQV map from the database.

        Args:
            request: An HTTP request.

        Returns:
            A Response object containing the PQV map as a dict, with status 200,
            on success. A Response with status_code 403 if the caller is not
            a member of the 'manager' group.
        """
        # Reject the request if the user is not in the "manager" group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group will be answered.',
                status.HTTP_403_FORBIDDEN,
            )

        return Response(PaperInfoService().get_pqv_map_dict())

    # POST /api/beta/pqvmap
    def post(self, request: Request) -> Response:
        """Create a PQV map and put it into the database.

        POST data determines the map to make. See below.

        This work is done by Huey, taking a blocking foreground approach.
        If 'count' is not provided, use the default suggested number.
        The request will be rejected if there is already a PQV map in place.
        (Note that the DELETE method is available on the same endpoint.)

        Callers are expected to do their own consistency checking. If some
        paper numbers have already been allocated through prenaming,
        it is strongly recommended to specify a range of paper numbers
        that includes all the ones to which names have already been assigned.
        Leaving some out will not cause a problem here, but the results may
        perplex both examiners and candidates on the day of the test.

        The HTTP response will be generated only after all the PQV map entries are
        built and installed. For large classes, this may take so long that the
        requester gives up and declares an HTTP timeout. This has not yet
        been observed in the wild, but we note it here in case some unfortunate
        colleague in the future needs a pointer on what's breaking.

        Args:
            request: An HTTP request.

        POST Data:
            number_to_produce: The number of papers to define, or None.
                (Given None, make the default number.)
            startn_value: The smallest integer to use for a test number.
                (Given None, use integer 1.)
            first_paper_num (optional): Text field from GUI radio buttons
                that short-circuits defaults for startn_value. Possible values
                are "0", "1", and "n".  TODO: consider removing this in the
                future, or even right now.

        Returns:
            An empty response with status code 204, on success. Status code 403
            if the user is not in the 'manager' group; status code 409 if the
            operation has been blocked by some kind of conflict.
        """
        # Reject the request if the user is not in the 'manager' group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can populate the database.',
                status.HTTP_403_FORBIDDEN,
            )

        if PaperInfoService.is_paper_database_populated():
            return _error_response(
                "PQV map is not empty. Consider deleting before re-generating.",
                status.HTTP_409_CONFLICT,
            )

        ntp_default = StagingStudentService().get_minimum_number_to_produce()
        ntp = request.POST.get("number_to_produce", ntp_default)
        number_to_produce = int(ntp)

        try:
            first_paper_hint = int(request.POST.get("first_paper_num", 1))
        except ValueError:
            first_paper_hint = 1

        startn = int(request.POST.get("startn_value", first_paper_hint))

        try:
            qvmap = PQVMappingService().make_version_map(
                number_to_produce, first=startn
            )
            PaperCreatorService.add_all_papers_in_qv_map(qvmap, background=False)
        except PlomDependencyConflict as err:
            return _error_response(err, status.HTTP_409_CONFLICT)

        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUT /api/beta/pqvmap
    def put(self, request: Request) -> Response:
        """Replace the PQV map with the one attached to the request.

        Not built yet! (But relevant infrastructure is available, thanks to others.)

        Args:
            request: An HTTP request, with a PQV map in the FILES container.

        Returns:
            Status code 501, not implemented, for now.
        """
        return _error_response(
            "PUT method not built yet!", status.HTTP_501_NOT_IMPLEMENTED
        )
