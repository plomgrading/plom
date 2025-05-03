# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status

from plom.plom_exceptions import PlomDependencyConflict
from plom_server.Papers.services import SpecificationService
from plom_server.Preparation.services import SourceService
from plom_server.Preparation.services.preparation_dependency_service import (
    assert_can_modify_sources,
)

from .utils import _error_response


class SourceOverview(APIView):
    """Handle non-specific transactions involving Assessment Sources."""

    # GET /api/v0/source
    def get(self, request: Request) -> Response:
        """Get overview info about assessment sources.

        Returns:
            (200) a list of dicts, with one entry for each source.
                  Number of sources is declared in the spec.
                  Each dict comes straight from SourceService, typically
                  {"version": int, "uploaded": bool, "hash": str}
            (404) There are no sources, and the number of sources
                  cannot be determined ... probably because there is
                  no spec.
        """
        if not SpecificationService.is_there_a_spec():
            return _error_response(
                "Server does not even have a spec.", status.HTTP_404_NOT_FOUND
            )

        LOS = SourceService.get_list_of_sources()
        return Response(LOS)


class SourceDetail(APIView):
    """Handle transactions involving specific assessment Sources."""

    # GET /api/v0/source/<int:ver>
    def get(self, request: Request, version: int) -> Response:
        """Get a copy of the numbered assessment source PDF.

        Returns:
            Http response 200 with the PDF file as the payload.
            A 404 response if that version isn't found.
        """
        abstract_django_file = SourceService._get_source_file(version)
        slug = SpecificationService.get_short_name_slug()
        if version is not None:
            try:
                return FileResponse(
                    abstract_django_file,
                    as_attachment=True,
                    filename=f"{slug}_source{version}.pdf",
                    # TODO: would this append junk if we cycle a few times?
                    # filename=abstract_django_file.name,
                )
            except ObjectDoesNotExist:
                return _error_response(
                    f"PDF for source {version} not found.", status.HTTP_404_NOT_FOUND
                )

    # POST /api/v0/source/<int:ver>
    def post(self, request: Request, version: int) -> Response:
        """Create, replace, or delete a source version.

        Args:
            request: An HTTP request in which the numbered spec is embedded in the FILES dict.
            version: The version number of the source to operate on.

        Returns:
            (200) Dict describing the freshly-uploaded source, just like for GET
            (400) File provided is absent or invalid (empty files are OK),
                  or version number out of range, or upload failed for some reason
            (401) User does not belong to "manager" group
            (409) Changing the source is not allowed.
                  Typically because the server is either too raw or too advanced.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can upload an assessment source.',
                status.HTTP_401_FORBIDDEN,
            )

        try:
            assert_can_modify_sources()
        except PlomDependencyConflict as e:
            return _error_response(
                e,
                status.HTTP_409_CONFLICT,
            )

        if "source_pdf" not in request.FILES:
            return _error_response(
                "No source PDF supplied.", status.HTTP_400_BAD_REQUEST
            )

        ListOfSources = SourceService.get_list_of_sources()
        if version < 0 or version > len(ListOfSources):
            return _error_response(
                f"Source version number {version} is invalid.",
                status.HTTP_409_CONFLICT,
            )

        SourceService.delete_source_pdf(version)

        source_pdf = request.FILES["source_pdf"]
        if source_pdf is not None and source_pdf.size > 0:
            try:
                success, message = SourceService.take_source_from_upload(
                    version, request.FILES["source_pdf"]
                )
            except PlomDependencyConflict as e:
                return _error_response(
                    f"Modifying source {version} is not allowed. {e}",
                    status.HTTP_409_CONFLICT,
                )

        if not success:
            return _error_response(message, status.HTTP_400_BAD_REQUEST)

        ListOfSources = SourceService.get_list_of_sources()
        sourcenotes = ListOfSources[version - 1]

        return Response(sourcenotes)

    # DELETE /api/v0/source/<int:ver>
    def delete(self, request: Request, version: int) -> Response:
        """Delete the specified source version.

        Args:
            request: An HTTP request object that will be ignored.
            version: The version number of the source to operate on.

        Returns:
            HTTP response 200 with the updated list of dicts as described
            in :class:`SourceOverview`.  200 is returned even in the case
            where no such source version exists (that's not an error).
            Only managers can do this; others get a 401.
            409 is returned if the source is "in use", typically b/c
            server configuration has progressed further.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can upload an assessment source.',
                status.HTTP_401_FORBIDDEN,
            )

        try:
            # note: no error if that source version does not exist
            SourceService.delete_source_pdf(version)
        except PlomDependencyConflict as e:
            return _error_response(e, status.HTTP_409_CONFLICT)

        LOS = SourceService.get_list_of_sources()
        return Response(LOS)
