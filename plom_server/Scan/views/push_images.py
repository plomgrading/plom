# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023 Andrew Rechnitzer

from django.http import Http404
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView

from ..services import ScanService


class PushAllPageImages(ScannerRequiredView):
    """Push all page-images that pass the QR validation checks."""

    def post(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        scanner.push_bundle_to_server(bundle, request.user)

        return HttpResponseClientRefresh()
