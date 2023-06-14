# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from django.urls import path

from StudentMarks.views import StudentMarkView, StudentMarkPaperView


urlpatterns = [
    path("", StudentMarkView.as_view(), name="student_marks"),
    path("<int:paper_num>/paper/", StudentMarkPaperView.as_view(), name="paper_num"),
]
