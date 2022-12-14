# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from django.http import Http404
from django_htmx.http import HttpResponseClientRefresh
from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanService
from Scan.models import ParseQR

class ChangeErrorImageState(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()
        
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        scanner.change_error_image_state(bundle, index)

        return HttpResponseClientRefresh()
