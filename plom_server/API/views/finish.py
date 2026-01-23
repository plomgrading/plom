# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025-2026 Aidan Murphy

from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework import status

from plom_server.Finish.services import ReassembleService, BuildSolutionService

from .utils import _error_response


class FinishReassembled(APIView):
    """API related to marked and reassembled papers."""

    # GET: /api/beta/finish/reassembled/{papernum}
    def get(self, request: Request, *, papernum: int) -> FileResponse:
        """API to download one reassembled paper.

        Only managers and lead_markers can access this, others will receive a 403.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if not ("manager" in group_list or "lead_marker" in group_list):
            return _error_response(
                'Only "manager" and "lead_marker" users can download reassembled papers',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            pdf_file, filename = ReassembleService.get_single_reassembled_file(papernum)
        except ObjectDoesNotExist as err:
            return _error_response(
                "Reassembled paper does not exist: perhaps not yet marked,"
                f" identified or reassemble is in-progress: {err}",
                status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(pdf_file, filename=filename, status=status.HTTP_200_OK)


class FinishReport(APIView):
    """API related to student reports."""

    # GET: /api/beta/finish/report/{papernum}
    def get(self, request: Request, *, papernum: int) -> FileResponse:
        """API to download a report for a given paper.

        Only managers and lead_markers can access this, others will receive a 403.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if not ("manager" in group_list or "lead_marker" in group_list):
            return _error_response(
                'Only "manager" and "lead_marker" users can download report files',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            pdf_file, filename = ReassembleService().get_single_student_report(papernum)
        except ObjectDoesNotExist as err:
            return _error_response(
                f"Report for paper {papernum} does not exist: perhaps the paper is"
                f" not yet marked, identified or reassemble is in-progress: {err}",
                status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(pdf_file, filename=filename, status=status.HTTP_200_OK)


class FinishSolution(APIView):
    """API related to solution files."""

    # GET: /api/beta/finish/solution/{papernum}
    def get(self, request: Request, *, papernum: int) -> FileResponse:
        """API to download a solution file for a given paper.

        Only managers and lead_markers can access this, others will receive a 403.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if not ("manager" in group_list or "lead_marker" in group_list):
            return _error_response(
                'Only "manager" and "lead_marker" users can download solution files',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            pdf_file, filename = BuildSolutionService().get_single_solution_pdf_file(
                papernum
            )
        except ObjectDoesNotExist as err:
            return _error_response(
                "Solution file does not exist: perhaps not yet assembled,"
                f" assembly is in-progress: {err}",
                status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(pdf_file, filename=filename, status=status.HTTP_200_OK)


class FinishUnmarked(APIView):
    """API related to unmarked papers."""

    # GET: /api/beta/finish/unmarked/{papernum}
    def get(self, request: Request, *, papernum: int) -> FileResponse:
        """API to download one unmarked paper.

        Only managers and lead_markers can access this,
        others will receive a 403.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if not ("manager" in group_list or "lead_marker" in group_list):
            return _error_response(
                'Only "manager" and "lead_marker" users can download reassembled papers',
                status.HTTP_403_FORBIDDEN,
            )

        try:
            pdf_bytestream = ReassembleService.get_unmarked_paper(papernum)
        except ValueError as err:
            return _error_response(
                f"Unable to retrieve the 'unmarked' paper: {err}",
                status.HTTP_404_NOT_FOUND,
            )
        # note: filename set in service function
        return FileResponse(pdf_bytestream, status=status.HTTP_200_OK)
