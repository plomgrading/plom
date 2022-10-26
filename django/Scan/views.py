# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

import pathlib
from datetime import datetime
from sys import prefix
import arrow
import json
from django.shortcuts import render
from django.http import HttpResponseRedirect, FileResponse, Http404, HttpResponse
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django_htmx.http import HttpResponseClientRefresh

from Base.base_group_views import ScannerRequiredView
from Papers.services import SpecificationService
from Scan.forms import BundleUploadForm
from Scan.services import (
    ScanService
)


class ScannerHomeView(ScannerRequiredView):
    """
    Display an upload form for bundle PDFs, and a dashboard of previously uploaded/staged
    bundles.
    """

    def build_context(self, user):
        context = super().build_context()
        scanner = ScanService()
        if not scanner.user_has_running_image_tasks(user):
            context.update(
                {
                    "form": BundleUploadForm(),
                    "bundle_splitting": False,
                }
            )
        else:
            splitting_bundle = scanner.get_bundle_being_split(user)
            context.update(
                {
                    "bundle_splitting": True,
                    "timestamp": splitting_bundle.timestamp,
                }
            )
        user_bundles = scanner.get_user_bundles(user)
        bundles = []
        for bundle in user_bundles:
            date_time = datetime.fromtimestamp(bundle.timestamp)
            bundles.append(
                {
                    "slug": bundle.slug,
                    "timestamp": bundle.timestamp,
                    "time_uploaded": arrow.get(date_time).humanize(),
                    "pages": scanner.get_n_images(bundle),
                    "n_read": scanner.get_n_complete_reading_tasks(bundle),
                }
            )
        context.update({"bundles": bundles})
        return context

    def get(self, request):
        context = self.build_context(request.user)

        # if a pdf-to-image task is fully complete, perform some cleanup
        if context["bundle_splitting"]:
            scanner = ScanService()
            bundle = scanner.get_bundle(context["timestamp"], request.user)
            n_completed = scanner.get_n_completed_page_rendering_tasks(bundle)
            n_total = scanner.get_n_page_rendering_tasks(bundle)
            if n_completed == n_total:
                scanner.page_splitting_cleanup(bundle)

        return render(request, "Scan/home.html", context)

    def post(self, request):
        context = self.build_context(request.user)
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
            return HttpResponseRedirect(reverse("scan_home"))
        else:
            context.update({"form": form})
            return render(request, "Scan/home.html", context)


class BundleSplittingProgressView(ScannerRequiredView):
    """
    Display a spinner and progress bar while image rendering happens in the background.
    """

    def get(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        context.update({"timestamp": timestamp})

        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        if not bundle:
            raise Http404()

        # if the splitting is already complete, redirect to the manage view
        n_completed = scanner.get_n_completed_page_rendering_tasks(bundle)
        n_total = scanner.get_n_page_rendering_tasks(bundle)
        if n_completed == n_total:
            scanner.page_splitting_cleanup(bundle)
            return HttpResponseRedirect(
                reverse("scan_manage_bundle", args=(timestamp, 0))
            )

        return render(request, "Scan/to_image_progress.html", context)


class BundleSplittingUpdateView(ScannerRequiredView):
    """
    Return an updated progress card to be displayed on the bundle splitting progress view.
    """

    def get(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        n_completed = scanner.get_n_completed_page_rendering_tasks(bundle)
        n_total = scanner.get_n_page_rendering_tasks(bundle)

        if n_completed == n_total:
            return HttpResponseClientRefresh()

        context.update(
            {
                "n_completed": n_completed,
                "n_total": n_total,
                "progress_percent": f"{int(n_completed / n_total * 100)}%",
                "timestamp": timestamp,
            }
        )

        return render(request, "Scan/fragments/to_image_card.html", context)


class ManageBundleView(ScannerRequiredView):
    """
    Let a user view an uploaded bundle and read its QR codes.
    """

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        n_pages = scanner.get_n_images(bundle)

        if index >= n_pages:
            raise Http404("Bundle page does not exist.")

        pages = [scanner.get_qr_code_reading_status(bundle, i) for i in range(n_pages)]
        qr_finished = scanner.is_bundle_reading_started(bundle)

        context.update(
            {
                "slug": bundle.slug,
                "timestamp": timestamp,
                "pages": pages,
                "qr_finished": qr_finished,
                "index": index,
                "one_index": index + 1,
                "total_pages": n_pages,
                "prev_idx": index - 1,
                "next_idx": index + 1,
            }
        )
        return render(request, "Scan/manage_bundle.html", context)


class UpdateQRProgressView(ScannerRequiredView):
    """
    Get the progress of a background QR code reading task.
    """

    def build_context(self, timestamp, user, index):
        context = super().build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, user)
        task_status = scanner.get_qr_code_reading_status(bundle, index)

        context.update(
            {
                "timestamp": timestamp,
                "index": index,
                "task_status": task_status,
            }
        )

        if task_status:
            context.update({"in_progress": True})
            qr_data = scanner.get_qr_code_results(bundle, index)
            if qr_data:
                code = list(qr_data.values())[0]  # get the first sub-dict
                qr_results = {
                    "paper_id": code["paper_id"],
                    "page_num": code["page_num"],
                    "version_num": code["version_num"],
                }
                context.update({"qr_results": qr_results})
            if task_status == "error":
                context.update(
                    {"error": scanner.get_qr_code_error_message(bundle, index)}
                )
        return context

    def get(self, request, timestamp, index):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context(timestamp, request.user, index)
        return render(request, "Scan/fragments/qr_code_panel.html", context)


class QRParsingProgressAlert(ScannerRequiredView):
    """
    Display and update an alert while QR code reading is in progress.
    """

    def get(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        context = self.build_context()
        scanner = ScanService()
        bundle = scanner.get_bundle(timestamp, request.user)
        context.update(
            {
                "reading_ongoing": scanner.is_bundle_reading_ongoig(bundle),
                "total_pages": scanner.get_n_images(bundle),
                "total_complete": scanner.get_n_complete_reading_tasks(bundle),
                "timestamp": timestamp,
            }
        )

        return render(request, "Scan/fragments/qr_code_alert.html", context)


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
        scanner.read_qr_codes(bundle)
        
        # parsed_QR = scanner.parse_qr_code(result)

        # Save qr codes to disk
        # bundle_dir_path = pathlib.Path(bundle.file_path).parent
        # bundle_image_path = bundle_dir_path / "pageImages"

        # for i in range(len(result)):
        #     with open(bundle_image_path / f"page{i}.png.qr", "w") as f:
        #         json.dump(result[i], f)

        # validate QRs
        # spec = SpecificationService().get_the_spec()
        # qrs = scanner.validate_qr_codes(bundle, spec)
        # print(qrs)

        # return HttpResponseRedirect(
        #     reverse("scan_manage_bundle", args=(str(timestamp)))
        # )

        return HttpResponseClientRefresh()
