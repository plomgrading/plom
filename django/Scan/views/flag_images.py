# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from Base.base_group_views import ScannerRequiredView
from django.http import Http404

from Scan.services.scan_service import ScanService


class FlagPageImage(ScannerRequiredView):
    """
    If a page image has an error, this method allows
    scanners to flag the page image to the manager.
    """
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        scanner = ScanService() 
        