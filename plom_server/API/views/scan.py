# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from Scan.services import ScanService
from .utils import _error_response


class ScanListBundles(APIView):
    """API related to all bundles."""

    def get(self, request: Request) -> Response:
        """API to list all bundles."""
        bundle_status = ScanService().staging_bundle_status()
        return Response(bundle_status, status=status.HTTP_200_OK)


class ScanMapBundle(APIView):
    """API related to mapping a bundle."""

    def post(
        self, request: Request, *, bundle_id: int, papernum: int, questions: str
    ) -> Response:
        """API to map the pages of a bundle onto questions."""
        print(bundle_id)
        print(papernum)
        print(questions)
        data = request.query_params
        print(data)
        question_idx_list = data.getlist("qidx")
        print(question_idx_list)
        papernum_qp = data.get("papernum")
        print(papernum_qp)
        # if questions is None:
        #     questions = "all"
        # many types possible for ``questions`` but here we always get a str
        return _error_response("WIP", status.HTTP_400_BAD_REQUEST)
        try:
            ScanService().map_bundle_pages_cmd(
                bundle_id=bundle_id, papernum=papernum, question_map=questions
            )
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        return Response({"hi": "hello"}, status=status.HTTP_200_OK)
