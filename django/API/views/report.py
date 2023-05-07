# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class REPspreadsheet(APIView):
    def get(self, request):
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
        # TODO
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
        # TODO
        canned = [
            [["10130103", "Vandeventer, Irene"], [1, 1, 0], [2, 1, 1], [3, 2, 5]],
            [["10152155", "Little, Abigail"], [1, 1, 0], [2, 1, 2], [3, 1, 5]],
            [["10203891", "Coleman, Ashley"], [1, 2, 5], [2, 1, 5], [3, 1, 5]],
        ]
        canned = canned[papernum % len(canned)]
        print(canned)
        return Response(canned, status=status.HTTP_200_OK)
