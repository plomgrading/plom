# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from Scan.views.qr_codes import UpdateQRProgressView
from django.http import Http404, HttpResponse
from Scan.services.scan_service import ScanService


class FlagPageImage(UpdateQRProgressView):
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
        flag_image = scanner.get_image(timestamp, request.user, index)
        flag_image.flagged = True
        flag_image.comment = "This page is folded, might have to rescan it."
        flag_image.save()

        return HttpResponse('<p>Image flagged to manager <i class="bi bi-check-circle text-success"></i></p>')


class DeleteErrorImage(UpdateQRProgressView):
    """
    """
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()
        
        scanner = ScanService()
        image = scanner.get_image(timestamp, request.user, index)
        image.delete()

        return HttpResponse()