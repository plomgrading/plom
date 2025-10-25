# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from plom_server.Finish.services import ReassembleService
from plom_server.Finish.services import StudentMarkService
from plom_server.Papers.models import Paper

from .utils import _error_response


class REPspreadsheet(APIView):
    """API related to spreadsheat-like data."""

    def get(self, request: HttpRequest) -> HttpResponse:
        """API to get information about all marked and ID papers, similar to the contents of Plom's `marks.csv`.

        Only managers and lead_markers can access this, others will receive a 403.

        Returns a list of dicts, with homogeneous keys, appropriate for the headers
        of a csv file, for example.
        """
        group_list = list(request.user.groups.values_list("name", flat=True))
        if not ("manager" in group_list or "lead_marker" in group_list):
            return _error_response(
                'Only "manager" and "lead_marker" users access spreadsheet data',
                status.HTTP_403_FORBIDDEN,
            )

        spreadsheet_data = StudentMarkService.get_all_marking_info_faster()
        return Response(
            spreadsheet_data,
            status=status.HTTP_200_OK,
        )


class REPidentified(APIView):
    def get(self, request: HttpRequest) -> HttpResponse:
        id_data = StudentMarkService().get_identified_papers()
        return Response(
            id_data,
            status=status.HTTP_200_OK,
        )


class REPcompletionStatus(APIView):
    def get(self, request: HttpRequest) -> HttpResponse:
        completion_data = ReassembleService().get_completion_status()
        return Response(
            completion_data,
            status=status.HTTP_200_OK,
        )


class REPcoverPageInfo(APIView):
    def get(self, request: HttpRequest, *, papernum: int) -> HttpResponse:
        # Return value looks like this:
        # [["10130103", "Vandeventer, Irene"], [1, 1, 0], [2, 1, 1], [3, 2, 5], [q, v, m]]
        service = ReassembleService()
        paper = get_object_or_404(Paper, paper_number=papernum)
        legacy_cover_page_info = service.get_legacy_cover_page_info(paper)
        return Response(legacy_cover_page_info, status=status.HTTP_200_OK)
