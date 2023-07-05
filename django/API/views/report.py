# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from Finish.services import ReassembleService

from Mark.services import MarkingTaskService


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
        # TODO: Identified, Marked, num_questions_marked
        # TODO: what time-stamp?  last-modified?
        canned = {
            "11": [False, True, 2, "2023-05-03T07:48:13.739950+00:00"],
            "12": [True, True, 3, "2023-05-03T07:48:13.751636+00:00"],
            "13": [True, True, 3, "2023-05-03T07:48:13.762651+00:00"],
            "14": [True, True, 3, "2023-05-03T07:48:13.775470+00:00"],
        }
        return Response(
            canned,
            status=status.HTTP_200_OK,
        )


class REPcoverPageInfo(APIView):
    def get(self, request, papernum):
        # Return value looks like this:
        # [["10130103", "Vandeventer, Irene"], [1, 1, 0], [2, 1, 1], [3, 2, 5]]
        service = MarkingTaskService()
        r = []
        # TODO: hardcoded
        r.append(["10130103", "Vandeventer, Irene"])
        # TODO: hardcoded for 3 questions
        for question in range(1, 3 + 1):
            annotation = service.get_latest_annotation(papernum, question)
            # TODO: see MgetAnnotations: extra sanity checking?
            # TODO: hard-coded version 1
            ver = 1
            r.append([question, ver, annotation.score])
        return Response(r, status=status.HTTP_200_OK)
