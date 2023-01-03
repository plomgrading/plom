# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse
from django_htmx.http import HttpResponseClientRefresh
from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanService
from Papers.services import ImageBundleService
from Scan.forms import ReplaceImageForm
from Scan.views import UpdateQRProgressView, ManageBundleView

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


class ReplacePageImage(ManageBundleView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()
        context = self.build_context(timestamp, request.user, index)
        form = ReplaceImageForm(request.POST, request.FILES)
        if form.is_valid():
            print("uploaded file")
            return HttpResponse("No error")
        else:
            error_message = "An error occurred replacing the page image."
            context.update({"replace_image_error_message": error_message})
            return render(request, "Scan/manage_bundle.html", context)
        
