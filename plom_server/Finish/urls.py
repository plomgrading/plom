# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.urls import path

from .views import (
    MarkingInformationView,
    MarkingInformationPaperView,
    ReassemblePapersView,
    StartOneReassembly,
    StartAllReassembly,
    CancelQueuedReassembly,
)


urlpatterns = [
    path("marking_info", MarkingInformationView.as_view(), name="marking_info"),
    path(
        "marking_info/<int:paper_num>/paper/",
        MarkingInformationPaperView.as_view(),
        name="paper_num",
    ),
    path(
        "marking_info/marks_download/",
        MarkingInformationView.marks_download,
        name="marks_download",
    ),
    path(
        "marking_info/ta_info_download/",
        MarkingInformationView.ta_info_download,
        name="ta_info_download",
    ),
    path("reassemble/", ReassemblePapersView.as_view(), name="reassemble_pdfs"),
    path(
        "reassemble/<int:paper_number>",
        StartOneReassembly.as_view(),
        name="reassemble_one_paper",
    ),
    path("reassemble/all", StartAllReassembly.as_view(), name="reassemble_all_pdfs"),
    path(
        "reassemble/queued",
        CancelQueuedReassembly.as_view(),
        name="reassemble_cancel_queued",
    ),
]
