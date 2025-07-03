# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView

# from rest_framework import serializers
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
                f"Dependency Conflict. The database cannot be cleaned right now. {err}",
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

        PIS = PaperInfoService()
        return Response(PIS.get_pqv_map_dict())

    # POST /api/beta/pqvmap, or /api/beta/pqvmap/<int:n>
    def post(self, request: Request, count: int | None = None) -> Response:
        """Create a PQV map with 'count' entries and put it into the database.

        This work is done by Huey, taking a blocking foreground approach.
        If 'count' is not provided, use the default suggested number.
        The request will be rejected if there is already a PQV map in place.
        (Note that the DELETE method is available on the same endpoint.)

        The response will be generated only after all the PQV map entries are
        built and installed. For large classes, this may take so long that the
        requester gives up and declares an HTTP timeout. This has not yet
        been observed in the wild, but we note it here in case some unfortunate
        colleague in the future needs a pointer on what's breaking.

        Args:
            request: An HTTP request.
            count: The number of papers to define, or None.
                (When count is 0, this works just like DELETE; when count is None,
                redirect to the same method but with count set to the default number.)

        Returns:
            An empty response with status code 204, on success. Status code 403
            if the user is not in the 'manager' group; status code 409 if the
            operation has been blocked by some kind of conflict.
        """
        # Reject the request if the user is not in the 'manager' group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can clean the database.',
                status.HTTP_403_FORBIDDEN,
            )

        if PaperInfoService.is_paper_database_populated():
            return _error_response(
                "PQV map is not empty. Consider deleting before re-generating.",
                status.HTTP_409_CONFLICT,
            )

        if count is None:
            count = StagingStudentService().get_minimum_number_to_produce()

        try:
            # Make the PQV map. Sorry for hard-coding the lowestpapernumber.
            lowestpapernumber = 1
            qvmap = PQVMappingService().make_version_map(count, first=lowestpapernumber)
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
