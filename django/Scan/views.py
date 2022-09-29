# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

import pathlib
from datetime import datetime
from django.shortcuts import render
from django.http import HttpResponseRedirect, FileResponse, Http404
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

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
            timestamp = datetime.timestamp(time_uploaded)
            return HttpResponseRedirect(
                reverse(
                    "scan_manage_bundle",
                    args=(slug, timestamp)
                )
            )
        else:
            context.update({"form": form})
            return render(request, "Scan/home.html", context)


class ManageBundleView(ScannerRequiredView):
    """
    Let a user view an uploaded bundle and read its QR codes.
    """

    def get(self, request, slug, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        context.update(
            {
                "slug": slug,
                "timestamp": timestamp
            }
        )
        return render(request, "Scan/manage_bundle.html", context)


class GetBundleView(ScannerRequiredView):
    """
    Return a user-uploaded bundle PDF
    """

    def get(self, request, slug, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()

        # TODO: scanner users can only access their own bundles.
        # The manager should be able to access all the scanner users' bundles?
        bundle = scanner.get_bundle(slug, timestamp, request.user)
        file_name = f"{slug}_{timestamp}.pdf"
        file_path = pathlib.Path("media") / bundle.user.username / "bundles" / file_name
        with open(file_path, "rb") as f:
            uploaded_file = SimpleUploadedFile(
                f"{slug}.pdf",
                f.read(),
                content_type="application/pdf",
            )
        return FileResponse(uploaded_file)
