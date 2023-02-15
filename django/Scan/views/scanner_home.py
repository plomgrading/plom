# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022 Brennen Chiu

import pathlib
from datetime import datetime
import arrow

from django.shortcuts import render
from django.http import HttpResponseRedirect, Http404, FileResponse
from django.urls import reverse
from django_htmx.http import HttpResponseClientRefresh
from django.core.files.uploadedfile import SimpleUploadedFile

from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanService
from Papers.services import ImageBundleService
from Progress.services import ManageScanService
from Scan.forms import BundleUploadForm


class ScannerHomeView(ScannerRequiredView):
    """
    Display an upload form for bundle PDFs, and a dashboard of previously uploaded/staged
    bundles.
    """

    def build_context(self, user):
        context = super().build_context()
        scanner = ScanService()
        mss = ManageScanService()

        total_papers = mss.get_total_test_papers()
        completed_papers = mss.get_completed_test_papers()
        percent_papers_complete = completed_papers / total_papers * 100

        total_pages = mss.get_total_pages()
        scanned_pages = mss.get_scanned_pages()
        percent_pages_complete = scanned_pages / total_pages * 100

        all_test_papers = mss.get_test_paper_list()

        context.update(
            {
                "completed_test_papers": completed_papers,
                "total_completed_test_papers": total_papers,
                "percent_papers_completed": int(percent_papers_complete),
                "completed_pages": scanned_pages,
                "total_completed_pages": total_pages,
                "percent_pages_completed": int(percent_pages_complete),
                "all_test_papers": all_test_papers,
            }
        )

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
        hash_pushed_bundle = False
        for bundle in user_bundles:
            date_time = datetime.fromtimestamp(bundle.timestamp)
            pages = scanner.get_n_images(bundle)
            n_pushed = scanner.get_n_pushed_images(bundle)
            flagged_pages = scanner.get_n_flagged_image(bundle)
            n_errors = scanner.get_n_error_image(bundle)
            if n_pushed == pages:
                scanner.push_bundle(bundle)

            disable_delete = (n_pushed > 0 and n_pushed < pages) or flagged_pages > 0
            bundles.append(
                {
                    "slug": bundle.slug,
                    "timestamp": bundle.timestamp,
                    "time_uploaded": arrow.get(date_time).humanize(),
                    "pages": pages,
                    "n_read": scanner.get_n_complete_reading_tasks(bundle),
                    # "n_pushed": n_pushed,
                    "disable_delete": disable_delete,
                    "n_errors": n_errors,
                    "bundle_pushed": bundle.pushed,
                }
            )
            if bundle.pushed:
                hash_pushed_bundle = True
            
        context.update({"bundles": bundles, "has_pushed_bundle": hash_pushed_bundle})
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
