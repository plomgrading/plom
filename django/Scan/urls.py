# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.urls import path

from Scan.views import ScannerHomeView


urlpatterns = [
    path("", ScannerHomeView.as_view(), name="scan_home"),
]
