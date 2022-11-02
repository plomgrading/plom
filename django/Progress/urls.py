# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.urls import path

from Progress.views import ScanOverview


urlpatterns = [
    path("scan/overview/", ScanOverview.as_view(), name="progress_scan_overview"),
]
