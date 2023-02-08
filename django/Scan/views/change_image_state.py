# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Brennen Chiu

import pathlib
from django.shortcuts import render, redirect
from django.http import Http404, HttpResponse
from django_htmx.http import HttpResponseClientRefresh
from bs4 import BeautifulSoup
from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanService
from Papers.services import ImageBundleService
from Scan.forms import ReplaceImageForm
from Scan.views import ManageBundleView
from Scan.models import (StagingImage)

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
            uploaded_pdf = data["pdf_doc"]
            time_uploaded = data["time_uploaded"]
            uploaded_image_hash = data["uploaded_image_hash"]
            
            scanner = ScanService()
            scanner.upload_replace_page(user, timestamp, time_uploaded, uploaded_pdf, index, uploaded_image_hash)
            success = "Successfully replaced image."
            context.update({"replace_image_success_message": success})
            return render(request, "Scan/manage_bundle.html", context)
        else:
            error_message = '""""' + str(form.errors) + '""""'
            parsed_error = BeautifulSoup(error_message, "html.parser")
            error = parsed_error.li.text[7:]
            context.update({"replace_image_error_message": error})
            return render(request, "Scan/manage_bundle.html", context)


class ChangeCollisionImageState(ScannerRequiredView):
    def post(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()
        
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        scanner.change_collision_image_state(bundle, index)
        # test = StagingImage.objects.all()
        # print(test[27:])


        return HttpResponseClientRefresh()
        
