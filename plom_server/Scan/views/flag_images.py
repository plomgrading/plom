# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu
# Copyright (C) 2023 Andrew Rechntizer
# Copyright (C) 2023 Colin B. Macdonald

from django.http import Http404, HttpResponse
from django.shortcuts import redirect

from Papers.services import ImageBundleService

from .qr_codes import UpdateQRProgressView
from ..services.scan_service import ScanService
from ..forms import FlagImageForm


class FlagPageImage(UpdateQRProgressView):
    """If a page image has an error, this method allows scanners to flag the page image to the manager."""

    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        scanner = ScanService()
        img_bundle_service = ImageBundleService()
        image = scanner.get_image(timestamp, request.user, index)
        stagged_bundle = image.bundle
        bundle = img_bundle_service.get_or_create_bundle(
            stagged_bundle.slug, stagged_bundle.pdf_hash
        )
        flag_image = scanner.get_error_image(bundle, index)
        form = FlagImageForm(request.POST)
        if form.is_valid():
            image.flagged = True
            flag_image.flagged = True
            flag_image.comment = (
                str(request.user.username) + "::" + str(form.cleaned_data["comment"])
            )
            image.save()
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
