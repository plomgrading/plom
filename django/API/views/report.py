# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from Mark.services import MarkingTaskService


class REPspreadsheet(APIView):
    def get(self, request):
        # TODO: q1v is question 1 version
        # TODO: q1m is question 1 mark
        canned = {
            "2": {
                "identified": True,
                "marked": True,
                "sid": "10130103",
                "sname": "Vandeventer, Irene",
                "q1v": 1,
                "q1m": 0,
                "q2v": 1,
                "q2m": 1,
                "q3v": 2,
                "q3m": 5,
                "last_update": "2023-05-03T07:48:13.751636+00:00",
            },
            "3": {
                "identified": True,
                "marked": True,
                "sid": "10152155",
                "sname": "Little, Abigail",
                "q1v": 1,
                "q1m": 0,
                "q2v": 1,
                "q2m": 2,
                "q3v": 1,
                "q3m": 5,
                "last_update": "2023-05-03T07:48:13.762651+00:00",
            },
            "4": {
                "identified": True,
                "marked": True,
                "sid": "10203891",
                "sname": "Coleman, Ashley",
                "q1v": 2,
                "q1m": 5,
                "q2v": 1,
                "q2m": 5,
                "q3v": 1,
                "q3m": 5,
                "last_update": "2023-05-03T07:48:13.775470+00:00",
            },
        }
        return Response(
            canned,
            status=status.HTTP_200_OK,
        )


class REPidentified(APIView):
    def get(self, request):
        # TODO
        canned = {
            "1": ["10050380", "Fink, Iris"],
            "2": ["10130103", "Vandeventer, Irene"],
            "3": ["10152155", "Little, Abigail"],
            "10": ["11135153", "Garcia, Theodore"],
            "11": ["12370103", "Khan, Josephine [randomly chosen]"],
            "12": ["12143240", "Horton, James [randomly chosen]"],
            "13": ["11770182", "Perkins, Albert [randomly chosen]"],
            "14": ["88882222", "Macdonald, Colin [randomly chosen]"],
            "15": [None, "No ID given"],
            "16": ["12368663", "Micheau, Barbara [randomly chosen]"],
        }
        return Response(
            canned,
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
