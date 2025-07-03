# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald
# Copyright (C) 2025 Aidan Murphy

from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework import status

from plom_server.Finish.services import ReassembleService

from .utils import _error_response


class FinishReassembled(APIView):
    """API related to bundles."""

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
            pdf_file = ReassembleService().get_single_reassembled_file(papernum)
        except ObjectDoesNotExist as err:
            return _error_response(
                "Reassembled paper does not exist: perhaps not yet marked,"
                f" identified or reassemble is in-progress: {err}",
                status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(pdf_file, status=status.HTTP_200_OK)


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
            pdf_bytestream = ReassembleService().get_unmarked_paper(papernum)
        except ValueError as err:
            return _error_response(
                f"Unable to retrieve the 'unmarked' paper: {err}",
                status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(pdf_bytestream, status=status.HTTP_200_OK)
