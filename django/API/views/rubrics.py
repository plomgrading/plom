# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class MgetRubricsByQuestion(APIView):
    def get(self, request, question):
        return Response([], status=status.HTTP_200_OK)


class MgetRubricPanes(APIView):
    def get(self, request, username, question):
        return Response({}, status=status.HTTP_200_OK)
