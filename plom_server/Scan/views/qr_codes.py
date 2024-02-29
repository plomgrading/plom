# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.http import HttpResponse
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView
from ..services import ScanService


class ReadQRcodesView(ScannerRequiredView):
    """Read QR codes of all pages in a bundle."""

    def post(self, request: HttpResponse, *, bundle_id: int):
        scanner = ScanService()
        scanner.read_qr_codes(bundle_id)

        return HttpResponseClientRefresh()
