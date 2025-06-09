from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from tempfile import NamedTemporaryFile
from plom_server.Rectangles.services import RectangleExtractor
from django.http import FileResponse
from .utils import _error_response
from rest_framework import status
from pathlib import Path


class RectangleExtractorView(APIView):
    # GET api/rectangle/{version}/{page_num}
    def get(self, request: Request, version: int, page_num: int) -> Response:
        """Get extracted regions of all scanned papers with the given version and page number.
        """
        print("RECEIVED REQUEST")
        try:
            rex = RectangleExtractor(version, page_num)
        except ValueError as err:
            return _error_response(
                f"Error: {err}",
                status.HTTP_400_BAD_REQUEST,
        )

        corners = request.query_params.dict()
        
        try:
            def get_float(val):
                if isinstance(val, list):
                    raise ValueError("Expected a single value for each corner, got a list")
                return float(val)
            
            left = get_float(corners["left"])
            right = get_float(corners["right"])
            top = get_float(corners["top"])
            bottom = get_float(corners["bottom"])
    
        except (TypeError, ValueError) as err:
            return _error_response(
                f"Error: {err}",
                status.HTTP_400_BAD_REQUEST,
            )

        tmpzip = NamedTemporaryFile(delete=False)
        try:
            rex.build_zipfile(tmpzip.name, left, top, right, bottom)
            response = FileResponse(
                tmpzip, filename=f"extracted_rectangles_v{version}_pg{page_num}.zip"
            )
            response['Content-Type'] = 'application/zip'
            print("RETURNED ZIP")
            return response
        finally:
            Path(tmpzip.name).unlink()


       
