# Copyright (C) 2025 Bryan Tanady

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from tempfile import NamedTemporaryFile
from plom_server.Rectangles.services import RectangleExtractor
from django.http import FileResponse
from .utils import _error_response
from rest_framework import status
from io import BytesIO


class RectangleExtractorView(APIView):
    # GET api/rectangle/{version}/{page_num}
    def get(
        self, request: Request, version: int, page_num: int, paper_num: int
    ) -> Response:
        """Get extracted region a scanned paper with the given version and page number."""
        try:
            rex = RectangleExtractor(version, page_num)
        except ValueError as err:
            return _error_response(
                f"Error: {err}",
                status.HTTP_400_BAD_REQUEST,
            )

        corners = request.query_params.dict()

        def get_float(val):
            if isinstance(val, list):
                raise ValueError("Expected a single value for each corner, got a list")
            return float(val)

        try:
            left = get_float(corners["left"])
            right = get_float(corners["right"])
            top = get_float(corners["top"])
            bottom = get_float(corners["bottom"])

        except (TypeError, ValueError) as err:
            return _error_response(
                f"Error: {err}",
                status.HTTP_400_BAD_REQUEST,
            )

        image_bytes = rex.extract_rect_region(
            paper_number=paper_num,
            left_f=left,
            top_f=top,
            right_f=right,
            bottom_f=bottom,
        )

        response = FileResponse(
            BytesIO(image_bytes),
            filename=f"extracted_rectangles_v{version}_pg{page_num}_paper{paper_num}.png",
        )
        response["Content-Type"] = "image/png"
        return response
