# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer

from __future__ import annotations

from datetime import datetime

import arrow

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django.http import HttpResponseRedirect, Http404, FileResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django_htmx.http import HttpResponseClientRefresh, HttpResponseClientRedirect

from Base.base_group_views import ScannerRequiredView
from Preparation.services import PapersPrinted
from Progress.services import ManageScanService
from ..services import ScanService
from ..forms import BundleUploadForm

from plom.plom_exceptions import PlomBundleLockedException


class ScannerHomeView(ScannerRequiredView):
    """Display an upload form for bundle PDFs, and a dashboard of previously uploaded/staged bundles."""

    def build_context(self):
        context = super().build_context()
        scanner = ScanService()
        mss = ManageScanService()

        total_papers = mss.get_total_test_papers()
        complete_papers = mss.get_number_completed_test_papers()
        incomplete_papers = mss.get_number_incomplete_test_papers()
        unused_papers = mss.get_number_unused_test_papers()

        context.update(
            {
                "complete_test_papers": complete_papers,
                "incomplete_test_papers": incomplete_papers,
                "unused_test_papers": unused_papers,
                "total_papers": total_papers,
                "form": BundleUploadForm(),
                "is_any_bundle_push_locked": False,
                "papers_have_been_printed": PapersPrinted.have_papers_been_printed(),
            }
        )
        staged_bundles = []
        pushed_bundles = []
        for bundle in scanner.get_all_staging_bundles():
            date_time = timezone.make_aware(datetime.fromtimestamp(bundle.timestamp))
            if bundle.has_page_images:
                cover_img_rotation = scanner.get_first_image(bundle).rotation
            else:
                cover_img_rotation = 0
            pages = scanner.get_n_images(bundle)
            if bundle.pushed:
                pushed_bundles.append(
                    {
                        "id": bundle.pk,
                        "slug": bundle.slug,
                        "timestamp": bundle.timestamp,
                        "time_uploaded": arrow.get(date_time).humanize(),
                        "username": bundle.user.username,
                        "pages": pages,
                        "cover_angle": cover_img_rotation,
                    }
                )
            else:
                staged_bundles.append(
                    {
                        "id": bundle.pk,
                        "slug": bundle.slug,
                        "timestamp": bundle.timestamp,
                        "time_uploaded": arrow.get(date_time).humanize(),
                        "username": bundle.user.username,
                        "pages": pages,
                        "cover_angle": cover_img_rotation,
                        "is_push_locked": bundle.is_push_locked,
                    }
                )
                # flag if any bundle is push-locked
                if bundle.is_push_locked:
                    context["is_any_bundle_push_locked"] = True

        context.update(
            {"pushed_bundles": pushed_bundles, "staged_bundles": staged_bundles}
        )
        return context

    def get(self, request) -> HttpResponse:
        context = self.build_context()
        return render(request, "Scan/home.html", context)

    def post(self, request) -> HttpResponse:
        context = self.build_context()
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

            # Note that this does take a timestamp instead of a bundle_pk, because that bundle does not yet exist in the database and so has no pk.
            ScanService().upload_bundle(
                bundle_file, slug, user, timestamp, pdf_hash, number_of_pages
            )

            return HttpResponseRedirect(reverse("scan_home"))
        else:
            # TODO - fix this error handling
            # context.update({"form": form})
            return render(request, "Scan/home.html", context)


class GetBundleView(ScannerRequiredView):
    """Return a user-uploaded bundle PDF."""

    def get(self, request: HttpResponse, *, bundle_id: int) -> HttpResponse:
        scanner = ScanService()

        bundle = scanner.get_bundle_from_pk(bundle_id)
        return FileResponse(
            bundle.pdf_file, filename=f"{bundle.slug}.pdf", as_attachment=True
        )


class GetStagedBundleFragmentView(ScannerRequiredView):
    """Return a user-uploaded bundle PDF."""

    def get(self, request, *, bundle_id: int) -> HttpResponse:
        """Rendered fragment of a staged but not pushed bundle.

        Args:
            request: the request.

        Keyword Args:
            bundle_id: which bundle?  Sometimes called the "pk" (private key)
                internally.

        Returns:
            A rendered HTML page.
        """
        scanner = ScanService()

        bundle = scanner.get_bundle_from_pk(bundle_id)
        n_known = scanner.get_n_known_images(bundle)
        n_unknown = scanner.get_n_unknown_images(bundle)
        n_extra = scanner.get_n_extra_images(bundle)
        n_extra_w_data = scanner.get_n_extra_images_with_data(bundle)
        n_discard = scanner.get_n_discard_images(bundle)
        n_errors = scanner.get_n_error_images(bundle)
        n_incomplete = scanner.get_bundle_number_incomplete_papers(bundle)
        if bundle.has_page_images:
            cover_img_rotation = scanner.get_first_image(bundle).rotation
        else:
            cover_img_rotation = 0

        context = {
            "bundle_id": bundle.pk,
            "timestamp": bundle.timestamp,
            "slug": bundle.slug,
            "when": arrow.get(bundle.timestamp).humanize(),
            "username": bundle.user.username,
            "number_of_pages": bundle.number_of_pages,
            "has_been_processed": bundle.has_page_images,
            "has_qr_codes": bundle.has_qr_codes,
            "is_mid_qr_read": scanner.is_bundle_mid_qr_read(bundle.pk),
            "is_push_locked": bundle.is_push_locked,
            "is_perfect": scanner.is_bundle_perfect(bundle.pk),
            "n_known": n_known,
            "n_unknown": n_unknown,
            "n_extra": n_extra,
            "n_extra_w_data": n_extra_w_data,
            "n_discard": n_discard,
            "n_errors": n_errors,
            "n_incomplete": n_incomplete,
            "cover_angle": cover_img_rotation,
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

        return render(request, "Scan/fragments/staged_bundle_row.html", context)

    def post(
        self, request: HttpRequest, *, bundle_id: int
    ) -> HttpResponseClientRefresh:
        scanner = ScanService()
        scanner.read_qr_codes(bundle_id)
        return HttpResponseClientRefresh()

    def delete(self, request: HttpRequest, *, bundle_id: int) -> HttpResponse:
        scanner = ScanService()
        try:
            scanner._remove_bundle(bundle_id)
        except PlomBundleLockedException:
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        except ObjectDoesNotExist as e:
            raise Http404(e)

        return HttpResponseClientRefresh()
