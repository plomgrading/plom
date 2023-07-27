# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.urls import path

from .views import MarkingInformationView, MarkingInformationPaperView


urlpatterns = [
    path("", MarkingInformationView.as_view(), name="marking_info"),
    path(
        "<int:paper_num>/paper/",
        MarkingInformationPaperView.as_view(),
        name="paper_num",
    ),
    path(
        "marks_download/", MarkingInformationView.marks_download, name="marks_download"
    ),
    path(
        "ta_info_download/",
        MarkingInformationView.ta_info_download,
        name="ta_info_download",
    ),
]
