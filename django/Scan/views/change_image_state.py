# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Brennen Chiu

import pathlib
from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse
from django_htmx.http import HttpResponseClientRefresh
from bs4 import BeautifulSoup
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
            data = form.cleaned_data
            user = request.user
            time_uploaded = data["time_uploaded"]
            uploaded_pdf = data["pdf_doc"]

            scanner = ScanService()
            scanner.upload_replace_page(user, timestamp, time_uploaded, uploaded_pdf, index)
            return HttpResponse("No error")
        else:
            error_message = '""""' + str(form.errors) + '""""'
            parsed_error = BeautifulSoup(error_message, "html.parser")
            error = parsed_error.li.text[7:]
            error_message = "An error occurred replacing the page image."
            context.update({"replace_image_error_message": error})
            return render(request, "Scan/manage_bundle.html", context)
        
