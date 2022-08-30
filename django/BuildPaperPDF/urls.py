from django.urls import path, include
from .views import (BuildPaperPDFs, GetPDFFile, GetCompressedPDFs)

urlpatterns = [
    path("", BuildPaperPDFs.as_view(), name="create_paperPDFs"),
    path("get/<int:paper_number>", GetPDFFile.as_view(), name="get_paperPDFs"),
    path("get_zip/", GetCompressedPDFs.as_view(), name="zip_paperPDFs"),
    # TODO: remeber to add <int: paper_number> back before get/
]
