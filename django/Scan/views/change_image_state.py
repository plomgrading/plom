# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from django.http import Http404
from django_htmx.http import HttpResponseClientRefresh
from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanService
from Papers.services import ImageBundleService
from Scan.forms import ReplaceImageForm

class ChangeErrorImageState(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()
        
        scanner = ScanService()
        img_bundle_service = ImageBundleService()
        bundle = scanner.get_bundle(timestamp, request.user)
        image = scanner.get_image(timestamp, request.user, index)
        stagged_bundle = image.bundle
        img_bundle = img_bundle_service.get_or_create_bundle(
            stagged_bundle.slug, stagged_bundle.pdf_hash
        )
        scanner.change_error_image_state(bundle, index, img_bundle)

        return HttpResponseClientRefresh()


class ReplacePageImage(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()
        form = ReplaceImageForm(request.POST, request.FILES)
        if form.is_valid():
            print("uploaded file")
        else:
            print("no file uploaded")
        

        return HttpResponseClientRefresh()
