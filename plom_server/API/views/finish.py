# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist
from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework import status

from Finish.services import ReassembleService

from .utils import _error_response


class FinishReassembled(APIView):
    """API related to bundles."""

    # GET: /api/beta/finish/reassembled/{papernum}
    def get(self, request: Request, *, papernum: int) -> FileResponse:
        """API to download one reassembled paper."""
        try:
            pdf_file = ReassembleService().get_single_reassembled_file(papernum)
        except ObjectDoesNotExist as err:
            return _error_response(
                "Reassembled paper does not exist: perhaps not yet marked,"
                f" identified or reassemble is in-progress: {err}",
                status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(pdf_file, status=status.HTTP_200_OK)
