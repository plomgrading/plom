# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2025 Colin B. Macdonald
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2025 Philip D. Loewen

from io import BytesIO

from django.http import FileResponse, StreamingHttpResponse

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework import status

from plom.plom_exceptions import PlomDependencyConflict

from plom_server.Papers.services import SpecificationService

from plom_server.Preparation.services.PapersPrinted import (
    set_papers_printed,
    have_papers_been_printed,
)

from plom_server.BuildPaperPDF.services import BuildPapersService

from .utils import _error_response


class papersToPrint(APIView):
    """Manipulate the files in the server's papersToPrint directory."""

    # DELETE /api/beta/paperstoprint
    def delete(self, request: Request) -> Response:
        """Delete all of the PDF files containing papers-to-print.

            This work is done by Huey.

        Args:
            request: An HTTP request.

        Returns:
            An empty response, with status 204, on success.
            Status 403 if the caller is not in the 'manager' group;
            status 409 if there is some other kind of conflict.
        """
        # Reject the request if the user is not in the "manager" group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can deal directly with papers to print.',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            BuildPapersService().reset_all_tasks()
        except PlomDependencyConflict as err:
            return _error_response(
                f"Request to reset papers rejected--dependency conflict; {err}.",
                status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    # GET /api/beta/paperstoprint/<int:papernumber>
    # GET /api/beta/paperstoprint/<str:action>
    # GET /api/beta/paperstoprint
    def get(
        self,
        request: Request,
        papernumber: int | None = None,
        action: str | None = None,
    ) -> Response:
        """Get papers-printed status, or paper images (one or all).

        Args:
            request: An HTTP request.
            papernumber (optional): Integer paper number of the PDF to return.
            action (optional): String "getprinted" or "ready" to request status info.

        Returns:
            For the URL /api/beta/paperstoprint/getprinted, return "True" or "False"
            in response to the assertion, "The papers have been printed."
            For the URL /api/beta/paperstoprint/ready, return "True" or "False"
            in response to the assertion, "The server holds a complete set of assessment PDFs."
            For the URL /api/beta/paperstoprint/42, return a streaming PDF of paper 42.
            For the URL /api/beta/paperstoprint, return a streaming ZIP of all papers.
            Return status 403 if the user is not in the 'manager' group, and status 404
            if the requested paper-image information was impossible to generate.
        """
        # Reject the request if the user is not in the "manager" group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can deal directly with papers to print.',
                status.HTTP_403_FORBIDDEN,
            )

        if action is not None:
            if action == "getprinted":
                flagvalue = have_papers_been_printed()
                return Response(f"{flagvalue}")
            if action == "ready":
                flagvalue = BuildPapersService().are_all_papers_built()
                return Response(f"{flagvalue}")
            else:
                return _error_response(
                    f"Invalid action '{action}'", status.HTTP_400_BAD_REQUEST
                )

        if papernumber is not None:
            papernumber = int(papernumber)
            # Return single PDF as requested by number
            # Very similar (hardly DRY) to adjacent method GetPDFFile.get()
            try:
                (
                    pdf_filename,
                    pdf_bytes,
                ) = BuildPapersService.get_paper_recommended_name_and_bytes(papernumber)
            except ValueError:
                return _error_response(
                    f"Paper {papernumber} not found", status.HTTP_404_NOT_FOUND
                )
            return FileResponse(
                BytesIO(pdf_bytes),
                filename=pdf_filename,
                content_type="application/pdf",
            )

        # Return streaming zip of all papersToPrint
        # Very similar (hardly DRY) to adjacent method GetStreamingZipOfPDFs.get()
        short_name = SpecificationService.get_short_name_slug()
        try:
            zgen = BuildPapersService.get_zipfly_generator(short_name)
        except ValueError:
            return _error_response(
                f"Papers for {short_name} not found", status.HTTP_404_NOT_FOUND
            )
        response = StreamingHttpResponse(zgen, content_type="application/octet-stream")
        response["Content-Disposition"] = f"attachment; filename={short_name}.zip"
        return response

    # POST /api/beta/paperstoprint/setprinted
    # POST /api/beta/paperstoprint/unsetprinted
    # POST /api/beta/paperstoprint
    def post(self, request: Request, action: str | None = None) -> Response:
        """Launch PDF-creation process, or manipulate the 'printed' flag.

        Plom builds individualized PDFS, one per paper, using
        parallel background threads managed by Huey. A well-formed
        POST request activates the task of building all such PDFs.
        The process is asynchronous, and may take a long time.
        To detect whether all the PDFs are ready, review the GET
        methods provided by this same class.

        Args:
            request: An HTTP request.
            action: One of 'setprinted', 'unsetprinted', or None.
                Use None to launch the creation process for all PDFs.

        Returns:
            An empty response, with status 204, if paper-building has launched.
            Status 403 if the caller is not in the 'manager' group;
            status 400 if there are already some papers to print,
            or there is some other kind of problem with the request;
            status 409 if there is some other kind of conflict.
        """
        # Reject the request if the user is not in the "manager" group.
        group_list = list(request.user.groups.values_list("name", flat=True))
        if "manager" not in group_list:
            return _error_response(
                'Only users in the "manager" group can deal directly with papers to print.',
                status.HTTP_403_FORBIDDEN,
            )

        if action is not None:
            if action == "setprinted":
                try:
                    set_papers_printed(True)
                except PlomDependencyConflict as e:
                    return _error_response(
                        e,
                        status.HTTP_409_CONFLICT,
                    )
                return Response(status=status.HTTP_204_NO_CONTENT)
            elif action == "unsetprinted":
                try:
                    set_papers_printed(False)
                except PlomDependencyConflict as e:
                    return _error_response(
                        e,
                        status.HTTP_409_CONFLICT,
                    )
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return _error_response(
                    f"Invalid action '{action}'", status.HTTP_400_BAD_REQUEST
                )

        # Here action is None, so the request is to make all the PDFs
        try:
            BuildPapersService().send_all_tasks()
        except PlomDependencyConflict as err:
            return _error_response(
                f"Request to build papers rejected--dependency conflict. {err}",
                status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
