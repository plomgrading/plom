# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from Scan.views.qr_codes import UpdateQRProgressView
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from Scan.services.scan_service import ScanService
from Scan.forms import FlagImageForm


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
        form = FlagImageForm(request.POST)
        if form.is_valid():
            flag_image.flagged = True
            flag_image.comment = (
                str(request.user.username) + "said " + str(form.cleaned_data["comment"])
            )
            flag_image.save()
            return redirect("scan_manage_bundle", timestamp, index)
        else:
            return HttpResponse("Form error!")


# put this into manager function instead
# class DeleteErrorImage(UpdateQRProgressView):
#     """
#     """
#     def post(self, request, timestamp, index):
#         try:
#             timestamp = float(timestamp)
#         except ValueError:
#             return Http404()

#         scanner = ScanService()
#         image = scanner.get_image(timestamp, request.user, index)
#         image.delete()

#         return HttpResponse()
