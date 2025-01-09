# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2025 Colin B. Macdonald

import hashlib
from datetime import datetime
from pathlib import Path

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from plom.plom_exceptions import PlomConflict
from Scan.services import ScanService
from .utils import _error_response


class ScanListBundles(APIView):
    """API related to bundles."""

    def get(self, request: Request) -> Response:
        """API to list all bundles."""
        bundle_status = ScanService().staging_bundle_status()
        return Response(bundle_status, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        """API to upload a new bundle."""
        print(request)
        print(request.data)
        user = request.user
        print((user, type(user)))
        pdf = request.FILES.get("pdf_file")
        print((pdf, type(pdf)))
        filename_stem = Path(pdf.name).stem
        if filename_stem.startswith("_"):
            s = "Bundle filenames cannot start with an underscore - we reserve those for internal use."
            return _error_response(s, status.HTTP_400_BAD_REQUEST)

        # TODO: BundleUploadForm is not used in this API endpoint and that's
        # unfortunate b/c it does some checks including a maximum upload size.

        slug = slugify(filename_stem)
        timestamp = datetime.timestamp(timezone.now())
        try:
            with pdf.open("rb") as f:
                file_bytes = f.read()
        except OSError as err:
            raise RuntimeError(f"dunno about this error handling: {err}")

        hashed = hashlib.sha256(file_bytes).hexdigest()

        # TODO: annoying we have to open it to read the md5sum
        try:
            bundle_id = ScanService.upload_bundle(pdf, slug, user, timestamp, hashed)
        except PlomConflict as e:
            return _error_response(e, status.HTTP_409_CONFLICT)

        # force_render: bool = False,
        # read_after: bool = False,

        return Response({"bundle_id": bundle_id}, status=status.HTTP_200_OK)


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
