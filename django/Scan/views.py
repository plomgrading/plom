# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates

import pathlib
from datetime import datetime
import arrow
import json
import shutil
from django.shortcuts import render
from django.http import HttpResponseRedirect, FileResponse, Http404
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView
from Papers.services import SpecificationService
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
        scanner = ScanService()
        user_bundles = scanner.get_user_bundles(request.user)
        bundles = []
        for bundle in user_bundles:
            date_time = datetime.fromtimestamp(bundle.timestamp)
            bundles.append(
                {
                    "slug": bundle.slug,
                    "timestamp": bundle.timestamp,
                    "time_uploaded": arrow.get(date_time).humanize(),
                }
            )
        context.update({"bundles": bundles})
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
            timestamp = datetime.timestamp(time_uploaded)
            scanner.upload_bundle(bundle_doc, slug, user, timestamp, pdf_hash)
            return HttpResponseRedirect(
                reverse("scan_manage_bundle", args=(timestamp,))
            )
        else:
            context.update({"form": form})
            return render(request, "Scan/home.html", context)


class ManageBundleView(ScannerRequiredView):
    """
    Let a user view an uploaded bundle and read its QR codes.
    """

    def get(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        n_images = scanner.get_n_images(bundle)
        context.update(
            {
                "slug": bundle.slug,
                "timestamp": timestamp,
                "images": [i for i in range(n_images)],
            }
        )
        return render(request, "Scan/manage_bundle.html", context)


class RemoveBundleView(ScannerRequiredView):
    """
    Delete an uploaded bundle
    """

    def delete(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        scanner.remove_bundle(timestamp, request.user)
        return HttpResponseClientRefresh()


class GetBundleView(ScannerRequiredView):
    """
    Return a user-uploaded bundle PDF
    """

    def get(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()

        # TODO: scanner users can only access their own bundles.
        # The manager should be able to access all the scanner users' bundles?
        bundle = scanner.get_bundle(timestamp, request.user)
        file_name = f"{timestamp}.pdf"
        file_path = pathlib.Path("media") / bundle.user.username / "bundles" / file_name
        with open(file_path, "rb") as f:
            uploaded_file = SimpleUploadedFile(
                f"{bundle.slug}.pdf",
                f.read(),
                content_type="application/pdf",
            )
        return FileResponse(uploaded_file)


class GetBundleImageView(ScannerRequiredView):
    """
    Return an image from a user-uploaded bundle
    """

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        image = scanner.get_image(timestamp, request.user, index)
        file_path = image.file_path
        with open(file_path, "rb") as f:
            uploaded_file = SimpleUploadedFile(
                f"page_{index}.png",
                f.read(),
                content_type="image/png",
            )
        return FileResponse(uploaded_file)


class ReadQRcodesView(ScannerRequiredView):
    """
    Read QR codes of all pages in a bundle
    """

    def post(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            return Http404()

        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        result = scanner.read_qr_codes(bundle)

        # Save qr codes to disk
        bundle_dir_path = pathlib.Path(bundle.file_path).parent
        bundle_image_path = bundle_dir_path / "pageImages"

        for i in range(len(result)):
            with open(bundle_image_path / f"page{i}.png.qr", "w") as f:
                json.dump(result[i], f)

        # validate QRs
        spec = SpecificationService().get_the_spec()
        qrs = scanner.validate_qr_codes(bundle, spec)
        print(qrs)

        return HttpResponseRedirect(
            reverse("scan_manage_bundle", args=(str(timestamp)))
        )
