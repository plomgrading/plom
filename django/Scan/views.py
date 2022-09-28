# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

from django.shortcuts import render
from django.http import HttpResponseRedirect

from Base.base_group_views import ScannerRequiredView
from Scan.forms import BundleUploadForm
from Scan.services import ScanService


class ScannerHomeView(ScannerRequiredView):
    """
    Hello, world!
    """

    def build_context(self):
        context = super().build_context()
        context.update(
            {
                "form": BundleUploadForm(),
            }
        )
        return context

    def get(self, request):
        context = self.build_context()
        return render(request, "Scan/home.html", context)

    def post(self, request):
        context = self.build_context()
        form = BundleUploadForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            user = request.user
            slug = data["slug"]
            time_uploaded = data["time_uploaded"]
            bundle_doc = data["pdf_doc"]
            pdf_hash = data["sha256"]

            scanner = ScanService()
            scanner.upload_bundle(bundle_doc, slug, user, time_uploaded, pdf_hash)
            return HttpResponseRedirect(".")
        else:
            context.update({"form": form})
            return render(request, "Scan/home.html", context)
