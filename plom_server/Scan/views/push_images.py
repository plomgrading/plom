# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Colin B. Macdonald

from django.http import HttpResponse
from django_htmx.http import HttpResponseClientRefresh, HttpResponseClientRedirect
from django.urls import reverse

from Base.base_group_views import ScannerRequiredView

from ..services import ScanService
from plom.plom_exceptions import PlomBundleLockedException


class PushAllPageImages(ScannerRequiredView):
    """Push all page-images that pass the QR validation checks."""

    def post(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        try:
            ScanService().push_bundle_to_server(bundle_id, request.user)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )

        return HttpResponseClientRefresh()
