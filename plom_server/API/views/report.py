# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald
# Copyright (C) 2023 Edith Coates

from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from Finish.services import ReassembleService

from Papers.models import Paper


class REPspreadsheet(APIView):
    def get(self, request):
        spreadsheet_data = ReassembleService().get_spreadsheet_data()
        return Response(
            spreadsheet_data,
            status=status.HTTP_200_OK,
        )


class REPidentified(APIView):
    def get(self, request):
        id_data = ReassembleService().get_identified_papers()
        return Response(
            id_data,
            status=status.HTTP_200_OK,
        )


class REPcompletionStatus(APIView):
    def get(self, request):
        completion_data = ReassembleService().get_completion_status()
        return Response(
            completion_data,
            status=status.HTTP_200_OK,
        )


class REPcoverPageInfo(APIView):
    def get(self, request, papernum):
        # Return value looks like this:
        # [["10130103", "Vandeventer, Irene"], [1, 1, 0], [2, 1, 1], [3, 2, 5]]
        service = ReassembleService()
        paper = get_object_or_404(Paper, paper_number=papernum)
        cover_page_info = service.get_cover_page_info(paper)
        student_info = service.get_paper_id_or_none(paper)
        if student_info:
            student_id, student_name = student_info
        else:
            student_id, student_name = None, None

        legacy_cover_page_info = [[student_id, student_name]]
        for row in cover_page_info:
            legacy_cover_page_info.append(row[1:])

        return Response(legacy_cover_page_info, status=status.HTTP_200_OK)
