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
from plom_server.Papers.services import SpecificationService
from plom_server.Preparation.services import SourceService

#
# from .utils import debugnote
from .utils import _error_response


class SourceOverview(APIView):
    """Handle non-specific transactions involving Assessment Sources."""

    # GET /api/v0/source
    def get(self, request: Request) -> Response:
        """Get overview info about assessment sources.

        Returns:
            (200) a list of dicts, with one entry for each source
                  sources declared in the spec. Each dict comes
                  straight from SourceService. Look there for details.
                  ("version": int, "uploaded": bool, "hash": str)
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
        """Get detailed info about a numbered assessment source.

        Returns:
            (200) Here is the info.
            (400) Requested source number is incompatible with the spec.
            (404) Info not found. (Maybe no spec exists, maybe some anomaly.)
        """
        if not SpecificationService.is_there_a_spec():
            return _error_response(
                "Server does not even have a spec.", status.HTTP_404_NOT_FOUND
            )

        # Exploit redundancy in list of source dicts to do extra error-checking.
        LOS = SourceService.get_list_of_sources()
        k = version - 1
        try:
            detail = LOS[k]
        except IndexError:
            N = len(LOS)
            return _error_response(
                f"Spec allows versions 1,...,{N}, but you referred to number {version}.",
                status.HTTP_400_BAD_REQUEST,
            )

        if detail["version"] == version:
            return Response(detail)

        return _error_response(
            f"Anomaly: {detail['version']:d} found in position {version:d}.",
            status.HTTP_404_NOT_FOUND,
        )

    # POST /api/v0/source
    def post(self, request: Request, version: int) -> Response:
        """Create, replace, or delete a source version.

        Args:
            request: An HTTP request in which the numbered spec is embedded in the FILES dict.
            version: The version number of the source to operate on.

        Returns:
            (200) Dict describing the freshly-uploaded source, just like for GET
            (400) No PDF file provided (empty files are OK), or version number out of range
            (401) User does not belong to "manager" group
            (404) Not used directly here, but could bubble up from a call to get(), above
            (409) Changing the source is not allowed. Typically because the server is in an advanced state.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can upload an assessment source.',
                status.HTTP_401_FORBIDDEN,
            )

        if "source_pdf" not in request.FILES:
            return _error_response(
                "No source PDF supplied.", status.HTTP_400_BAD_REQUEST
            )

        checkthis = self.get(request, version)
        if checkthis.status_code != 200:
            return _error_response(checkthis.reason_phrase, checkthis.status_code)

        source_pdf = request.FILES["source_pdf"]
        if source_pdf.size == 0:
            SourceService.delete_source_pdf(version)
        else:
            try:
                SourceService.delete_source_pdf(version)
                success, message = SourceService.take_source_from_upload(
                    version, request.FILES["source_pdf"]
                )
            except PlomDependencyConflict as e:
                return _error_response(
                    f"Modifying source {version} is not allowed. Details: " + f"{e}",
                    status.HTTP_409_CONFLICT,
                )

        return self.get(request, version)
