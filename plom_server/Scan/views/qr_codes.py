# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Andrew Rechnitzer
# Copyright (C) 2023 Colin B. Macdonald

from django.shortcuts import render
from django.http import Http404
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView
from Papers.services import ImageBundleService
from ..services import ScanService


class ReadQRcodesView(ScannerRequiredView):
    """Read QR codes of all pages in a bundle."""

    def post(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        scanner.read_qr_codes(bundle.pk)

        return HttpResponseClientRefresh()
