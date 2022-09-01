from django.urls import path, include
from .views import (
    BuildPaperPDFs, 
    GetPDFFile, 
    GetCompressedPDFs,
    UpdatePDFTable,
    StartAllPDFs,
    StartOnePDF,
    CancelOnePDF,
)

urlpatterns = [
    path("", BuildPaperPDFs.as_view(), name="create_paperPDFs"),
    path("update/", UpdatePDFTable.as_view(), name="update_paperPDFs"),
    path("get/<int:paper_number>", GetPDFFile.as_view(), name="get_paperPDFs"),
    path("get_zip/", GetCompressedPDFs.as_view(), name="zip_paperPDFs"),
    path("start/all/", StartAllPDFs.as_view(), name='start_all_PDFs'),
    path("start/<int:paper_number>", StartOnePDF.as_view(), name='start_one_PDF'),
    path("cancel/<int:paper_number>", CancelOnePDF.as_view(), name='cancel_one_PDF'),
]
