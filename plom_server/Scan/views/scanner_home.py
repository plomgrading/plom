# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2022-2023 Edith Coates
# Copyright (C) 2022-2023 Brennen Chiu
# Copyright (C) 2023 Natalie Balashov
# Copyright (C) 2023-2025 Colin B. Macdonald
# Copyright (C) 2023-2024 Andrew Rechnitzer
# Copyright (C) 2024 Aidan Murphy
# Copyright (C) 2025 Philip D. Loewen

from datetime import datetime
from typing import Any

import arrow

from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.http import HttpRequest, HttpResponse, Http404, FileResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django_htmx.http import HttpResponseClientRefresh, HttpResponseClientRedirect
from django.conf import settings

from plom_server.Base.base_group_views import ScannerRequiredView
from plom_server.Preparation.services import PapersPrinted
from ..services import ScanService, ManageScanService
from ..forms import BundleUploadForm

from plom.misc_utils import format_int_list_with_runs
from plom.plom_exceptions import PlomBundleLockedException


class ScannerOverview(ScannerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        mss = ManageScanService()

        total_papers = mss.get_total_papers()
        completed_papers = mss.get_number_completed_papers()
        incomplete_papers = mss.get_number_incomplete_papers()
        pushed_bundles = mss.get_number_pushed_bundles()
        unpushed_bundles = mss.get_number_unpushed_bundles()
        discards = mss.get_discarded_page_info()

        context.update(
            {
                "total_papers": total_papers,
                "completed_papers": completed_papers,
                "incomplete_papers": incomplete_papers,
                "pushed_bundles": pushed_bundles,
                "unpushed_bundles": unpushed_bundles,
                "number_of_discards": len(discards),
            }
        )
        return render(request, "Scan/overview.html", context)


class ScannerStagedView(ScannerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        scanner = ScanService()
        staged_bundles = []
        for bundle in scanner.get_all_staging_bundles():
            # only keep staged not pushed bundles
            if bundle.pushed:
                continue
            date_time = timezone.make_aware(datetime.fromtimestamp(bundle.timestamp))
            if bundle.has_page_images:
                cover_img_rotation = scanner.get_first_image(bundle).rotation
            else:
                cover_img_rotation = 0
            pages = scanner.get_n_images(bundle)
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
        context["staged_bundles"] = staged_bundles
        return render(request, "Scan/show_staged_bundles.html", context)


class ScannerPushedView(ScannerRequiredView):
    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        scanner = ScanService()
        pushed_bundles = []

        for bundle in scanner.get_all_staging_bundles():
            # only keep pushed bundles
            if not bundle.pushed:
                continue
            date_time = timezone.make_aware(datetime.fromtimestamp(bundle.timestamp))
            if bundle.has_page_images:
                cover_img_rotation = scanner.get_first_image(bundle).rotation
            else:
                cover_img_rotation = 0
            n_pages = scanner.get_n_images(bundle)
            _papers = scanner.get_bundle_paper_numbers(bundle)
            pretty_print_paper_list = format_int_list_with_runs(_papers)
            n_papers = len(_papers)
            pushed_bundles.append(
                {
                    "id": bundle.pk,
                    "slug": bundle.slug,
                    "timestamp": bundle.timestamp,
                    "time_uploaded": arrow.get(date_time).humanize(),
                    "username": bundle.user.username,
                    "n_pages": n_pages,
                    "n_papers": n_papers,
                    "pretty_print_paper_list": pretty_print_paper_list,
                    "cover_angle": cover_img_rotation,
                }
            )
        context["pushed_bundles"] = pushed_bundles
        return render(request, "Scan/show_pushed_bundles.html", context)


class ScannerUploadView(ScannerRequiredView):
    def build_context(self) -> dict[str, Any]:
        context = super().build_context()
        scanner = ScanService()
        context.update(
            {
                "form": BundleUploadForm(),
                "is_any_bundle_push_locked": False,
                "papers_have_been_printed": PapersPrinted.have_papers_been_printed(),
                "bundle_size_limit": settings.MAX_BUNDLE_SIZE / 1024 / 1024,
                "bundle_page_limit": settings.MAX_BUNDLE_PAGES,
            }
        )
        uploaded_bundles = []
        for bundle in scanner.get_all_staging_bundles():
            date_time = timezone.make_aware(datetime.fromtimestamp(bundle.timestamp))
            n_pages = scanner.get_n_images(bundle)
            uploaded_bundles.append(
                {
                    "id": bundle.pk,
                    "slug": bundle.slug,
                    "time_uploaded": arrow.get(date_time).humanize(),
                    "username": bundle.user.username,
                    "n_pages": n_pages,
                    "is_pushed": bundle.pushed,
                    "hash": bundle.pdf_hash,
                }
            )
        context.update({"uploaded_bundles": uploaded_bundles})
        return context

    def get(self, request: HttpRequest) -> HttpResponse:
        context = self.build_context()
        return render(request, "Scan/bundle_upload.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        form = BundleUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            # we can get the errors from the form and pass them into the context
            # unfortunately form.errors is a dict of lists, so lets flatten it a bit.
            # see = https://docs.djangoproject.com/en/5.0/ref/forms/api/#django.forms.Form.errors
            error_list: list[str] = sum(form.errors.values(), [])
            messages.add_message(request, messages.ERROR, error_list)
            return HttpResponseClientRefresh()

        data = form.cleaned_data  # this checks the file really is a valid PDF
        user = request.user
        slug = data["slug"]
        bundle_file = data["pdf"]
        pdf_hash = data["sha256"]
        number_of_pages = data["number_of_pages"]
        timestamp = datetime.timestamp(data["time_uploaded"])
        ScanService.upload_bundle(
            bundle_file,
            slug,
            user,
            timestamp=timestamp,
            pdf_hash=pdf_hash,
            number_of_pages=number_of_pages,
            force_render=data["force_render"],
            read_after=data["read_after"],
        )
        if len(pdf_hash) >= (12 + 12 + 3):
            brief_hash = pdf_hash[:12] + "..." + pdf_hash[-12:]
        else:
            brief_hash = pdf_hash
        messages.add_message(
            request,
            messages.INFO,
            (
                f"Uploaded {slug} with {number_of_pages} pages "
                f"and hash {brief_hash}. "
                "Background processing started."
            ),
        )
        return HttpResponseClientRefresh()


class GetBundleView(ScannerRequiredView):
    """Return a user-uploaded bundle PDF."""

    def get(self, request: HttpRequest, *, bundle_id: int) -> HttpResponse:
        scanner = ScanService()

        bundle = scanner.get_bundle_from_pk(bundle_id)
        return FileResponse(
            bundle.pdf_file, filename=f"{bundle.slug}.pdf", as_attachment=True
        )


class GetStagedBundleFragmentView(ScannerRequiredView):
    """Various http methods for a staged-but-not-pushed user-uploaded bundle PDF."""

    def get(self, request: HttpRequest, *, bundle_id: int) -> HttpResponse:
        """Rendered fragment for one row of a staged bundle.

        Args:
            request: the request.

        Keyword Args:
            bundle_id: which bundle?  Sometimes called the "pk" (primary key)
                internally.

        Returns:
            A rendered HTML fragment to be inserted into a complete
            page using htmx.
        """
        scanner = ScanService()

        bundle = scanner.get_bundle_from_pk(bundle_id)
        _papers = scanner.get_bundle_paper_numbers(bundle)
        pretty_print_paper_list = format_int_list_with_runs(_papers)
        n_papers = len(_papers)
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

        from ..models import PagesToImagesChore, ManageParseQRChore

        try:
            _ = PagesToImagesChore.objects.get(bundle=bundle)
            _proc_status = _.get_status_display()
            _proc_msg = _.message
        except PagesToImagesChore.DoesNotExist:
            _proc_status = None
            _proc_msg = ""
        try:
            _ = ManageParseQRChore.objects.get(bundle=bundle)
            _read_status = _.get_status_display()
            _read_msg = _.message
        except ManageParseQRChore.DoesNotExist:
            _read_status = None
            _read_msg = ""

        is_waiting_or_processing = False
        if _proc_status in ("Queued", "Starting", "Running"):
            is_waiting_or_processing = True
        if _read_status in ("Queued", "Starting", "Running"):
            is_waiting_or_processing = True
        is_error = _proc_status == "Error" or _read_status == "Error"
        error_msg = _proc_msg + _read_msg

        context = {
            "bundle_id": bundle.pk,
            "timestamp": bundle.timestamp,
            "slug": bundle.slug,
            "when": arrow.get(bundle.timestamp).humanize(),
            "username": bundle.user.username,
            "proc_chore_status": _proc_status,
            "readQR_chore_status": _read_status,
            "number_of_pages": bundle.number_of_pages,
            "has_been_processed": bundle.has_page_images,
            "has_qr_codes": bundle.has_qr_codes,
            "is_waiting_or_processing": is_waiting_or_processing,
            "is_error": is_error,
            "error_msg": error_msg,
            "is_mid_qr_read": scanner.is_bundle_mid_qr_read(bundle.pk),
            "is_push_locked": bundle.is_push_locked,
            "is_perfect": scanner.is_bundle_perfect(bundle.pk),
            "n_papers": n_papers,
            "pretty_print_paper_list": pretty_print_paper_list,
            "n_known": n_known,
            "n_unknown": n_unknown,
            "n_extra": n_extra,
            "n_extra_w_data": n_extra_w_data,
            "n_discard": n_discard,
            "n_errors": n_errors,
            "n_incomplete": n_incomplete,
            "cover_angle": cover_img_rotation,
        }
        numpgs = context["number_of_pages"]
        if not context["has_been_processed"]:
            done = scanner.get_bundle_split_completions(bundle.pk)
            context.update(
                {
                    "number_of_split_pages": done,
                    "percent_split": 0 if numpgs is None else (100 * done) // numpgs,
                }
            )
        if context["is_mid_qr_read"]:
            done = scanner.get_bundle_qr_completions(bundle.pk)
            context.update(
                {
                    "number_of_read_pages": done,
                    "percent_read": 0 if numpgs is None else (100 * done) // numpgs,
                }
            )

        return render(request, "Scan/fragments/staged_bundle_row.html", context)

    def post(
        self, request: HttpRequest, *, bundle_id: int
    ) -> HttpResponseClientRefresh:
        """Triggers a qr-code read."""
        scanner = ScanService()
        scanner.read_qr_codes(bundle_id)
        return HttpResponseClientRefresh()

    def delete(self, request: HttpRequest, *, bundle_id: int) -> HttpResponse:
        """Triggers deletion of the bundle."""
        scanner = ScanService()
        try:
            scanner.remove_bundle_by_pk(bundle_id)
        except PlomBundleLockedException as err:
            messages.add_message(request, messages.ERROR, f"{err}")
            return HttpResponseClientRedirect(
                reverse("scan_bundle_lock", args=[bundle_id])
            )
        except ObjectDoesNotExist as e:
            raise Http404(e)

        return HttpResponseClientRedirect(reverse("scan_list_staged"))
