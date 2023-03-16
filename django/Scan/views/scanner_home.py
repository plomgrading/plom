# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov

import pathlib
from datetime import datetime
from django.utils import timezone
import arrow

from django.shortcuts import render
from django.http import HttpResponseRedirect, Http404, FileResponse
from django.urls import reverse
from django_htmx.http import HttpResponseClientRefresh
from django.core.files.uploadedfile import SimpleUploadedFile

from Base.base_group_views import ScannerRequiredView

from Scan.services import ScanService
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
                "form": BundleUploadForm(),
                "bundle_splitting": False,
            }
        )
        user_bundles = scanner.get_user_bundles(user)
        staged_bundles = []
        pushed_bundles = []
        for bundle in user_bundles:
            date_time = timezone.make_aware(datetime.fromtimestamp(bundle.timestamp))
            pages = scanner.get_n_images(bundle)
            if bundle.pushed:
                pushed_bundles.append(
                    {
                        "slug": bundle.slug,
                        "timestamp": bundle.timestamp,
                        "time_uploaded": arrow.get(date_time).humanize(),
                        "pages": pages,
                    }
                )
            else:
                staged_bundles.append(
                    {
                        "slug": bundle.slug,
                        "timestamp": bundle.timestamp,
                        "time_uploaded": arrow.get(date_time).humanize(),
                        "pages": pages,
                    }
                )

        context.update(
            {"pushed_bundles": pushed_bundles, "staged_bundles": staged_bundles}
        )
        return context

    def get(self, request):
        context = self.build_context(request.user)

        # if a pdf-to-image task is fully complete, perform some cleanup
        # if context["bundle_splitting"]:
        #     scanner = ScanService()
        #     bundle = scanner.get_bundle(context["timestamp"], request.user)
        #     n_completed = scanner.get_n_completed_page_rendering_tasks(bundle)
        #     n_total = scanner.get_n_page_rendering_tasks(bundle)
        #     if n_completed == n_total:
        #         scanner.page_splitting_cleanup(bundle)

        return render(request, "Scan/home.html", context)

    def post(self, request):
        context = self.build_context(request.user)
        form = BundleUploadForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data  # this checks the file really is a valid PDF

            user = request.user
            slug = data["slug"]
            time_uploaded = data["time_uploaded"]
            bundle_file = data["pdf"]
            pdf_hash = data["sha256"]
            number_of_pages = data["number_of_pages"]
            timestamp = datetime.timestamp(time_uploaded)

            ScanService().upload_bundle(
                bundle_file, slug, user, timestamp, pdf_hash, number_of_pages
            )

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


class GetStagedBundleFragmentView(ScannerRequiredView):
    """
    Return a user-uploaded bundle PDF
    """

    def get(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()

        bundle = scanner.get_bundle(timestamp, request.user)
        n_known = scanner.get_n_known_images(bundle)
        n_errors = scanner.get_n_error_images(bundle)
        context = {
            "timestamp": timestamp,
            "slug": bundle.slug,
            "when": arrow.get(timestamp).humanize(),
            "number_of_pages": bundle.number_of_pages,
            "has_been_processed": bundle.has_page_images,
            "has_qr_codes": bundle.has_qr_codes,
            "is_mid_qr_read": scanner.is_bundle_mid_qr_read(bundle.pk),
            "is_perfect": scanner.is_bundle_perfect(bundle.pk),
            "n_known": n_known,
            "n_errors": n_errors,
        }
        if not context["has_been_processed"]:
            done = scanner.get_bundle_split_completions(bundle.pk)
            context.update(
                {
                    "number_of_split_pages": done,
                    "percent_split": (100 * done) // context["number_of_pages"],
                }
            )
        if context["is_mid_qr_read"]:
            done = scanner.get_bundle_qr_completions(bundle.pk)
            context.update(
                {
                    "number_of_read_pages": done,
                    "percent_read": (100 * done) // context["number_of_pages"],
                }
            )

        return render(request, "Scan/fragments/staged_bundle_card.html", context)

    def post(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        bundle = scanner.get_bundle_from_timestamp(timestamp)
        scanner.read_qr_codes(bundle.pk)
        return HttpResponseClientRefresh()

    def delete(self, request, timestamp):
        try:
            timestamp = float(timestamp)
        except ValueError:
            raise Http404()

        scanner = ScanService()
        scanner.remove_bundle(timestamp, request.user)
        return HttpResponseClientRefresh()
