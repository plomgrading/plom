# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2023 Brennen Chiu
# Copyright (C) 2023 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, APIException
from rest_framework import status

from Rubrics.services import RubricService


class MgetRubricsByQuestion(APIView):
    def get(self, request, question):
        rs = RubricService()
        all_rubric_data = rs.get_rubrics(question=question)
        return Response(all_rubric_data, status=status.HTTP_200_OK)


class MgetRubricPanes(APIView):
    def get(self, request, username, question):
        rs = RubricService()
        pane = rs.get_rubric_pane(request.user, question)
        return Response(pane, status=status.HTTP_200_OK)

    def put(self, request, username, question):
        rs = RubricService()
        config = request.data["rubric_config"]
        rs.update_rubric_pane(request.user, question, config)
        return Response(status=status.HTTP_200_OK)


class McreateRubric(APIView):
    def put(self, request):
        rs = RubricService()
        try:
            rubric = rs.create_rubric(request.data["rubric"])
            return Response(rubric.key, status=status.HTTP_200_OK)
        except (ValidationError, NotImplementedError):
            raise APIException(
                detail="Invalid rubric", code=status.HTTP_406_NOT_ACCEPTABLE
            )


class MmodifyRubric(APIView):
    def patch(self, request, key):
        rs = RubricService()
        try:
            rubric = rs.modify_rubric(key, request.data["rubric"])
            return Response(rubric.key, status=status.HTTP_200_OK)
        except (ValidationError, NotImplementedError):
            raise APIException(
                detail="Invalid rubric data", code=status.HTTP_406_NOT_ACCEPTABLE
            )
