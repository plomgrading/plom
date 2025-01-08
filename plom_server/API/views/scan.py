# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

from django.core.exceptions import ObjectDoesNotExist
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

    def post(self, request: Request, *, bundle_id: int, page: int) -> Response:
        """API to map the pages of a bundle onto questions."""
        print(bundle_id)
        print(page)
        data = request.query_params
        print(data)
        question_idx_list = data.getlist("qidx")
        try:
            question_idx_list = [int(n) for n in question_idx_list]
        except ValueError as e:
            return _error_response(
                f"Non-integer qidx: {e}", status.HTTP_400_BAD_REQUEST
            )
        print(question_idx_list)
        papernum = data.get("papernum")
        print(papernum)
        print(type(papernum))
        # if questions is None:
        #     questions = "all"
        # many types possible for ``questions`` but here we always get a str
        # return _error_response("WIP", status.HTTP_400_BAD_REQUEST)

        # TODO: error handling to deal with: mapping the same page twice, currently an integrity error
        try:
            ScanService().map_bundle_page(
                bundle_id, page, papernum=papernum, question_indices=question_idx_list
            )
        except ValueError as e:
            return _error_response(e, status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as e:
            return _error_response(
                f"Probably no bundle id {bundle_id} or page {page}: {e}",
                status.HTTP_404_NOT_FOUND,
            )
        return Response({"hi": "hello"}, status=status.HTTP_200_OK)
