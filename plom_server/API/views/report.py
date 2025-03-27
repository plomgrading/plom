# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from plom_server.Finish.services import ReassembleService
from plom_server.Finish.services import StudentMarkService

from plom_server.Papers.models import Paper


class REPspreadsheet(APIView):
    def get(self, request: HttpRequest) -> HttpResponse:
        spreadsheet_data = StudentMarkService().get_spreadsheet_data()
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
