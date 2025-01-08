# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.http import HttpRequest, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from Scan.services import ScanService
from .utils import _error_response


class ScanListBundles(APIView):
    def get(self, request: HttpRequest) -> HttpResponse:
        bundle_status = ScanService().staging_bundle_status()
        return Response(bundle_status, status=status.HTTP_200_OK)


class ScanMapBundle(APIView):
    def post(
        self, request: HttpRequest, *, bundle_id: int, papernum: int, questions: str
    ) -> HttpResponse:
        print(bundle_id)
        print(papernum)
        print(questions)
        # if questions is None:
        #     questions = "all"
        # many types possible for ``questions`` but here we always get a str
        try:
            ScanService().map_bundle_pages_cmd(
                bundle_id=bundle_id, papernum=papernum, question_map=questions
            )
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        return Response({"hi": "hello"}, status=status.HTTP_200_OK)
