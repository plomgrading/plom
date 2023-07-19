# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Divy Patel

from django.urls import path

from Reports import views


urlpatterns = [
    path("", views.ReportLandingPageView.as_view(), name="reports_landing"),
]
