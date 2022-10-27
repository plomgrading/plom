# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from rest_framework.views import APIView
from rest_framework.response import Response

from Papers.services import SpecificationService


class QuestionMaxMark(APIView):
    """
    Return the max mark for a given question.
    """

    def get(self, request):
        data = request.query_params
        question = int(data["q"])
        version = int(data["v"])

        spec = SpecificationService()
        return Response(spec.get_question_mark(question))
