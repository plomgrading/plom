# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel
# Copyright (C) 2023 Julian Lapenna

from django.urls import path

from . import views


urlpatterns = [
    path("", views.ReportLandingPageView.as_view(), name="reports_landing"),
    path(
        "report_download/",
        views.ReportLandingPageView.report_download,
        name="report_download",
    ),
]
