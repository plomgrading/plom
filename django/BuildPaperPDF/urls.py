# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

from django.urls import path
from .views import (
    BuildPaperPDFs,
    GetPDFFile,
    GetCompressedPDFs,
    GetStreamingZipOfPDFs,
    UpdatePDFTable,
    StartAllPDFs,
    StartOnePDF,
    CancelAllPDf,
    CancelOnePDF,
    RetryAllPDF,
    DeleteAllPDF,
)

urlpatterns = [
    path("", BuildPaperPDFs.as_view(), name="create_paperPDFs"),
    path("update/", UpdatePDFTable.as_view(), name="update_paperPDFs"),
    path("get/<int:paper_number>", GetPDFFile.as_view(), name="get_paperPDFs"),
    path("get_zip/", GetCompressedPDFs.as_view(), name="zip_paperPDFs"),
    path("get_zip_stream/", GetStreamingZipOfPDFs.as_view(), name="zip_stream_paperPDFs"),
    path("start/all/", StartAllPDFs.as_view(), name="start_all_PDFs"),
    path("start/<int:paper_number>", StartOnePDF.as_view(), name="start_one_PDF"),
    path("cancel/all", CancelAllPDf.as_view(), name="cancel_all_PDFs"),
    path("cancel/<int:paper_number>", CancelOnePDF.as_view(), name="cancel_one_PDF"),
    path("retry/all", RetryAllPDF.as_view(), name="retry_all_PDFs"),
    path("delete/all/", DeleteAllPDF.as_view(), name="delete_all_PDFs"),
]
